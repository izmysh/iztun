"""Profile editing and switching regressions, without touching the host network."""
import hashlib
import io
import json
import tempfile
import unittest
from contextlib import ExitStack, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from test_helper import HELPER as h

CONFIG = "[Interface]\nAddress = 10.0.0.2/32\n[Peer]\nAllowedIPs = 0.0.0.0/0\n"


class ProfileTests(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        directory = Path(self.stack.enter_context(tempfile.TemporaryDirectory()))
        for key, value in {"CONFIG_DIR": directory / "configs", "STATE_DIR": directory / "state",
                           "TRASH_DIR": directory / "configs/.trash"}.items():
            self.stack.enter_context(patch.object(h, key, value))
        h.ensure_dirs()
        with redirect_stdout(io.StringIO()):
            h.cmd_import(CONFIG, "demo")
            h.cmd_import(CONFIG, "old")
        # Files in this non-root test belong to the test runner, not root.
        self.stack.enter_context(patch.object(h, "checked_profile", side_effect=h.profile_path))
        read_regular = h.read_regular
        self.stack.enter_context(patch.object(h, "read_regular", side_effect=lambda path, limit=h.MAX_CONFIG_BYTES, **kw: read_regular(path, limit)))
        self.stack.enter_context(patch.object(h, "active_interfaces", return_value=set()))
        self.stack.enter_context(patch.object(h, "service_properties", return_value={"ActiveState": "inactive"}))
        self.stack.enter_context(redirect_stdout(io.StringIO()))

    def payload(self, text=CONFIG + "# edited\n"):
        return json.dumps({"text": text, "revision": hashlib.sha256(CONFIG.encode()).hexdigest()})

    def test_unicode_rename_does_not_change_interface_or_config(self):
        h.cmd_rename("demo", "Работа — офис")
        self.assertEqual(h.display_name("demo"), "Работа — офис")
        self.assertEqual(h.profile_path("demo").read_text(), CONFIG)
        self.assertEqual(h.label_path("demo").stat().st_mode & 0o777, 0o600)

    def test_rename_rejects_empty_long_and_control_names(self):
        for label in (" ", "x" * 81, "bad\nname", "bad\x7fname"):
            with self.assertRaises(RuntimeError):
                h.cmd_rename("demo", label)

    def test_editor_read_returns_exact_config_and_revision(self):
        with redirect_stdout(io.StringIO()) as output:
            h.cmd_read_config("demo")
        data = json.loads(output.getvalue())
        self.assertEqual(data["text"], CONFIG)
        self.assertEqual(data["revision"], hashlib.sha256(CONFIG.encode()).hexdigest())

    def test_save_keeps_private_backup_and_replaces_atomically(self):
        h.cmd_save_config("demo", self.payload())
        self.assertEqual((h.CONFIG_DIR / "demo.conf.previous").read_text(), CONFIG)
        self.assertEqual(h.profile_path("demo").read_text(), CONFIG + "# edited\n")
        self.assertEqual(h.profile_path("demo").stat().st_mode & 0o777, 0o600)
        self.assertFalse(list(h.CONFIG_DIR.glob(".write-*")))

    def test_save_rejects_stale_editor(self):
        h.cmd_save_config("demo", self.payload())
        with self.assertRaisesRegex(RuntimeError, "changed since"):
            h.cmd_save_config("demo", self.payload(CONFIG + "# stale\n"))

    def test_save_rejects_hooks_without_touching_original(self):
        with self.assertRaises(RuntimeError):
            h.cmd_save_config("demo", self.payload(CONFIG.replace("[Peer]", "PostUp = bad\n[Peer]")))
        self.assertEqual(h.profile_path("demo").read_text(), CONFIG)

    def test_save_rejects_active_or_starting_tunnel(self):
        with patch.object(h, "active_interfaces", return_value={"demo"}):
            with self.assertRaisesRegex(RuntimeError, "Disconnect"):
                h.cmd_save_config("demo", self.payload())
        with patch.object(h, "service_properties", return_value={"ActiveState": "activating"}):
            with self.assertRaisesRegex(RuntimeError, "Disconnect"):
                h.cmd_save_config("demo", self.payload())

    def test_save_backup_does_not_follow_symlink(self):
        outside = h.CONFIG_DIR.parent / "outside"
        outside.write_text("preserve")
        (h.CONFIG_DIR / "demo.conf.previous").symlink_to(outside)
        h.cmd_save_config("demo", self.payload())
        self.assertEqual(outside.read_text(), "preserve")
        self.assertFalse((h.CONFIG_DIR / "demo.conf.previous").is_symlink())

    def test_full_tunnel_switch_stops_previous_before_starting_new(self):
        events = []
        with patch.object(h, "find_full_tunnel_conflict", return_value="old"), \
             patch.object(h, "force_cleanup", side_effect=lambda n: events.append(("stop", n))), \
             patch.object(h, "start_profile", side_effect=lambda n: events.append(("start", n))):
            h.cmd_up("demo")
        self.assertEqual(events, [("stop", "old"), ("start", "demo")])
        self.assertTrue(h.paused_path("old").exists())

    def test_failed_switch_restores_previous(self):
        with patch.object(h, "find_full_tunnel_conflict", return_value="old"), \
             patch.object(h, "force_cleanup"), \
             patch.object(h, "start_profile", side_effect=[RuntimeError("failed"), None]) as start:
            with self.assertRaisesRegex(RuntimeError, "previous tunnel was restored"):
                h.cmd_up("demo")
        self.assertEqual([call.args[0] for call in start.call_args_list], ["demo", "old"])
        self.assertFalse(h.paused_path("old").exists())

    def test_failed_restore_is_reported_honestly(self):
        with patch.object(h, "find_full_tunnel_conflict", return_value="old"), \
             patch.object(h, "force_cleanup"), \
             patch.object(h, "start_profile", side_effect=RuntimeError("failed")):
            with self.assertRaisesRegex(RuntimeError, "could not be restored"):
                h.cmd_up("demo")
        self.assertIn("could not be restored", h.read_last_error("old"))

    def test_split_tunnel_does_not_stop_other_profiles(self):
        with patch.object(h, "read_profile_metadata", return_value={"full_tunnel": False}), \
             patch.object(h, "force_cleanup") as cleanup, patch.object(h, "start_profile"):
            h.cmd_up("demo")
        cleanup.assert_not_called()

    def test_switch_checks_target_before_disconnecting(self):
        with patch.object(h, "checked_profile", side_effect=RuntimeError("invalid")), \
             patch.object(h, "force_cleanup") as cleanup:
            with self.assertRaisesRegex(RuntimeError, "invalid"):
                h.cmd_up("demo")
        cleanup.assert_not_called()


if __name__ == "__main__":
    unittest.main()
