"""Regression tests for privilege boundaries and failed network transactions."""
import io
import json
import socket
import tempfile
import unittest
from contextlib import ExitStack, redirect_stdout
from pathlib import Path
from unittest.mock import Mock, patch

from test_helper import HELPER as h

CONFIG = "[Interface]\nAddress = 10.0.0.2/32\n[Peer]\nAllowedIPs = 0.0.0.0/0\n"


class SecurityTests(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.directory = Path(self.stack.enter_context(tempfile.TemporaryDirectory()))
        for key, value in {"CONFIG_DIR": self.directory / "configs", "STATE_DIR": self.directory / "state",
                           "TRASH_DIR": self.directory / "configs/.trash"}.items():
            self.stack.enter_context(patch.object(h, key, value))
        h.ensure_dirs()

    def test_import_takes_contents_not_privileged_file_path(self):
        source = self.directory / "private.conf"
        source.write_text(CONFIG)
        with self.assertRaises(RuntimeError):
            h.cmd_import(str(source), "demo")
        self.assertFalse(h.profile_path("demo").exists())

    def test_rejects_all_hook_forms_before_persisting(self):
        for directive in ("PostUp = touch /tmp/exploit", "pReUp=bad", "PostDown", "SaveConfig = true"):
            with self.subTest(directive=directive), self.assertRaises(RuntimeError):
                h.cmd_import(CONFIG.replace("[Peer]", directive + "\n[Peer]"), "demo")
        self.assertFalse(h.profile_path("demo").exists())

    def test_rejects_control_characters_and_oversize(self):
        for config in (CONFIG + "\0", CONFIG + "#" * 65536):
            with self.assertRaises(RuntimeError):
                h.cmd_import(config, "demo")

    def test_names_cannot_be_options_or_directory_components(self):
        for name in (".", "..", "-x", "../../root", "a/b", "demo\n"):
            with self.subTest(name=name), self.assertRaises(SystemExit):
                h.profile_name(name)

    def test_import_never_follows_a_symbolic_link(self):
        target = self.directory / "outside"
        target.write_text("preserve")
        (h.CONFIG_DIR / "demo.conf").symlink_to(target)
        with self.assertRaises(RuntimeError):
            h.cmd_import(CONFIG, "demo")
        self.assertEqual(target.read_text(), "preserve")

    def test_import_does_not_overwrite_existing_profile(self):
        with redirect_stdout(io.StringIO()):
            h.cmd_import(CONFIG, "demo")
        with self.assertRaises(RuntimeError):
            h.cmd_import(CONFIG + "# replacement", "demo")
        self.assertEqual(h.profile_path("demo").read_text(), CONFIG)
        self.assertEqual(h.profile_path("demo").stat().st_mode & 0o777, 0o600)

    def test_rejects_reserved_routing_table_and_firewall_mark(self):
        for option in ("Table = 254", "FwMark = 254", "MTU = $(id)"):
            with self.assertRaises(RuntimeError):
                h.validate_config(CONFIG.replace("[Peer]", option + "\n[Peer]"))

    def test_two_half_routes_are_also_full_tunnel(self):
        path = h.profile_path("demo")
        path.write_text(CONFIG.replace("0.0.0.0/0", "0.0.0.0/1, 128.0.0.0/1"))
        self.assertTrue(h.read_profile_metadata(path)["full_tunnel"])

    def test_subprocess_error_never_returns_stderr_secrets(self):
        result = Mock(returncode=1, stdout="", stderr="invalid field MY-CUSTOM-SECRET")
        with patch.object(h.subprocess, "run", return_value=result):
            with self.assertRaises(RuntimeError) as error:
                h.run(["/usr/bin/awg", "show"])
        self.assertNotIn("MY-CUSTOM-SECRET", str(error.exception))

    def request(self, payload):
        server, client = socket.socketpair()
        self.addCleanup(server.close)
        self.addCleanup(client.close)
        client.sendall(json.dumps(payload).encode())
        client.shutdown(socket.SHUT_WR)
        with patch.object(h, "peer_is_authorized", return_value=True):
            h.serve_connection(server)
        return json.loads(client.recv(65536))

    def test_socket_rejects_root_only_operations_and_malformed_requests(self):
        for payload in ([], {"args": []}, {"args": ["service-up", "demo"]}, {"args": ["recover"]}):
            self.assertFalse(self.request(payload)["ok"])

    def test_socket_enforces_size_limit(self):
        connection = Mock()
        connection.recv.return_value = b"x" * (h.MAX_REQUEST_BYTES + 1)
        with patch.object(h, "peer_is_authorized", return_value=True):
            h.serve_connection(connection)
        self.assertFalse(json.loads(connection.sendall.call_args.args[0])["ok"])

    def test_socket_requires_authorized_peer(self):
        connection = Mock()
        with patch.object(h, "peer_is_authorized", return_value=False):
            h.serve_connection(connection)
        connection.recv.assert_not_called()
        self.assertFalse(json.loads(connection.sendall.call_args.args[0])["ok"])

    def test_concurrent_network_mutation_is_rejected(self):
        with h.operation_lock(), self.assertRaisesRegex(RuntimeError, "already in progress"):
            h.dispatch(["up", "demo"])

    def test_manual_disconnect_cancels_recovery_even_with_autostart(self):
        record = {"name": "demo", "active": False, "service_active": False, "enabled": True}
        self.assertEqual(h.recovery_candidates([record]), [record])
        h.paused_path("demo").touch()
        self.assertEqual(h.recovery_candidates([record]), [])

    def test_boot_start_checks_conflict_before_any_network_mutation(self):
        path = h.profile_path("demo")
        path.write_text(CONFIG)
        with patch.object(h, "checked_profile", return_value=path), \
             patch.object(h, "active_interfaces", return_value=set()), \
             patch.object(h, "find_full_tunnel_conflict", return_value="other"), \
             patch.object(h, "run") as run:
            with self.assertRaisesRegex(RuntimeError, "already active"):
                h.service_up("demo")
            run.assert_not_called()

    def test_failed_handshake_calls_down_and_records_error(self):
        path = h.profile_path("demo")
        path.write_text(CONFIG)
        with patch.object(h, "checked_profile", return_value=path), \
             patch.object(h, "active_interfaces", side_effect=[set(), {"demo"}, {"demo"}]), \
             patch.object(h, "find_full_tunnel_conflict", return_value=None), \
             patch.object(h, "verify_handshake", side_effect=RuntimeError("No handshake")), \
             patch.object(h, "run", return_value="") as run:
            with self.assertRaisesRegex(RuntimeError, "No handshake"):
                h.service_up("demo")
            self.assertIn(([h.AWG_QUICK, "down", path],), [call.args for call in run.call_args_list])
            self.assertIn("No handshake", h.read_last_error("demo"))

    def test_failed_cleanup_is_not_reported_as_success(self):
        path = h.profile_path("demo")
        path.write_text(CONFIG)
        def run(args, **kwargs):
            if args[:2] == [h.AWG_QUICK, "down"]:
                raise RuntimeError("cleanup failed")
            return ""
        with patch.object(h, "checked_profile", return_value=path), \
             patch.object(h, "active_interfaces", side_effect=[set(), {"demo"}, {"demo"}]), \
             patch.object(h, "find_full_tunnel_conflict", return_value=None), \
             patch.object(h, "verify_handshake", side_effect=RuntimeError("No handshake")), \
             patch.object(h, "run", side_effect=run):
            with self.assertRaisesRegex(RuntimeError, "cleanup needs attention"):
                h.service_up("demo")

    def test_peer_endpoint_is_not_confused_with_allowed_routes(self):
        dump = "secret\tpublic\tport\npublic\tsecret\t198.51.100.1:443\t0.0.0.0/0\t123\t20\t30\t25\n"
        with patch.object(h, "run", return_value=dump):
            stats = h.peer_stats("demo")
        self.assertEqual(stats, {"latest_handshake": 123, "rx": 20, "tx": 30, "endpoint": "198.51.100.1:443"})

    def test_ipv6_probe_is_attempted_when_ipv4_unavailable(self):
        from unittest.mock import MagicMock
        probe = MagicMock()
        with patch.object(h.socket, "socket", side_effect=[OSError("IPv4 unavailable"), probe]), \
             patch.object(h, "peer_stats", return_value={"latest_handshake": 123}):
            h.verify_handshake("demo")
        opened = probe.__enter__.return_value
        opened.setsockopt.assert_called_with(socket.SOL_SOCKET, socket.SO_BINDTODEVICE, b"demo\0")
        opened.sendto.assert_called_with(b"", ("2001:db8::1", 9))


if __name__ == "__main__":
    unittest.main()
