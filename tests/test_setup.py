import importlib.util
from importlib.machinery import SourceFileLoader
import os
from pathlib import Path
import stat
from types import SimpleNamespace
import unittest
from unittest.mock import patch

source = Path(__file__).resolve().parents[1] / "src/iztun-session-setup"
loader = SourceFileLoader("session_setup", str(source))
spec = importlib.util.spec_from_loader(loader.name, loader)
setup = importlib.util.module_from_spec(spec)
loader.exec_module(setup)


class SetupTests(unittest.TestCase):
    def setUp(self):
        self.account = SimpleNamespace(pw_uid=1000, pw_gid=1000, pw_name="demo", pw_dir="/home/demo")
        patches = [
            patch.object(setup.os, "getuid", return_value=0),
            patch.dict(os.environ, {"SUDO_UID": "1000", "LD_PRELOAD": "untrusted"}, clear=True),
            patch.object(setup.pwd, "getpwuid", return_value=self.account),
            patch.object(Path, "lstat", return_value=SimpleNamespace(st_mode=stat.S_IFDIR | 0o700, st_uid=1000)),
            patch.object(Path, "stat", return_value=SimpleNamespace(st_mode=stat.S_IFSOCK | 0o600, st_uid=1000)),
            patch.object(Path, "is_symlink", return_value=False),
            patch.object(setup.os, "getgrouplist", return_value=[1000, 982]),
        ]
        for hook in patches:
            hook.start()
            self.addCleanup(hook.stop)
        self.run_hook = patch.object(setup.subprocess, "run")
        self.spawn_hook = patch.object(setup.subprocess, "Popen")
        self.run = self.run_hook.start()
        self.spawn = self.spawn_hook.start()
        self.spawn.return_value.poll.return_value = None
        self.cgroup_hook = patch.object(Path, "read_text", autospec=True, side_effect=lambda path:
                                       "0::/setup.service\n" if str(path) == "/proc/self/cgroup"
                                       else "0::/user.slice/app-test.scope\n")
        self.cgroup_hook.start()
        self.addCleanup(self.cgroup_hook.stop)
        self.addCleanup(self.run_hook.stop)
        self.addCleanup(self.spawn_hook.stop)

    def rejected(self, args):
        with self.assertRaises((RuntimeError, KeyError, OSError)):
            setup.setup(args)
        self.run.assert_not_called()
        self.spawn.assert_not_called()

    def test_no_root_or_missing_arguments(self):
        with patch.object(setup.os, "getuid", return_value=1000):
            self.rejected(["wayland-0", "", ""])
        self.rejected([])

    def test_requires_non_root_caller_uid(self):
        for value in ("", "0", "-1", "demo", "1000;evil", "9999999999"):
            with self.subTest(uid=value), patch.dict(os.environ, {"SUDO_UID": value}):
                self.rejected(["wayland-0", "", ""])

    def test_runtime_owner_mode_and_type(self):
        for uid, mode in ((0, stat.S_IFDIR | 0o700), (1000, stat.S_IFDIR | 0o777), (1000, stat.S_IFLNK | 0o700)):
            with self.subTest(uid=uid, mode=mode), patch.object(Path, "lstat", return_value=SimpleNamespace(st_uid=uid, st_mode=mode)):
                self.rejected(["wayland-0", "", ""])

    def test_rejects_symlink_session_socket(self):
        with patch.object(Path, "is_symlink", return_value=True):
            self.rejected(["wayland-0", "", ""])

    def test_rejects_remote_or_unsafe_display(self):
        for args in (["../../evil", "", ""], ["", "host:0", ""], ["", "", ""]):
            with self.subTest(args=args):
                self.rejected(args)

    def test_fixed_command_and_privilege_drop(self):
        setup.setup(["wayland-0", ":0", "/home/demo/.Xauthority"])
        self.assertEqual(self.run.call_args.args[0], ["/usr/sbin/usermod", "-aG", "amneziawg", "--", "demo"])
        self.assertEqual(self.spawn.call_args.args[0], ["/usr/bin/systemd-run", "--user", "--scope", "--collect", "--quiet", "--", "/usr/bin/iztun"])
        arguments = self.spawn.call_args.kwargs
        self.assertEqual((arguments["user"], arguments["group"], arguments["extra_groups"]), (1000, 1000, [1000, 982]))
        self.assertEqual(arguments["cwd"], "/home/demo")
        self.assertNotIn("LD_PRELOAD", arguments["env"])
        self.assertNotIn("SUDO_UID", arguments["env"])
        self.assertEqual(arguments["env"]["WAYLAND_DISPLAY"], "wayland-0")

    def test_failed_group_setup_never_launches_gui(self):
        self.run.side_effect = setup.subprocess.CalledProcessError(1, "usermod")
        with self.assertRaises(setup.subprocess.SubprocessError):
            setup.setup(["wayland-0", "", ""])
        self.spawn.assert_not_called()

    def test_failed_desktop_launch_is_reported(self):
        self.spawn.return_value.poll.return_value = 1
        with self.assertRaisesRegex(RuntimeError, "Desktop launch failed"):
            setup.setup(["wayland-0", "", ""])

    def test_desktop_launch_deadline_terminates_child(self):
        with patch.object(setup.time, "monotonic", side_effect=[0, 6]), \
             self.assertRaisesRegex(RuntimeError, "timed out"):
            setup.setup(["wayland-0", "", ""])
        self.spawn.return_value.terminate.assert_called_once()

    def test_package_identity_and_authorization_dependencies(self):
        self.cgroup_hook.stop()
        root = source.parents[1]
        package = (root / "packaging/build-deb.sh").read_text()
        self.assertIn("package_name=iztun", package)
        self.assertIn("Replaces: amneziawg-linux-gui", package)
        self.assertIn("sudo, ssh-askpass-gnome", package)
