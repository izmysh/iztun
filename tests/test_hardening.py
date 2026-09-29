import io
import json
import os
import tempfile
import unittest
from contextlib import ExitStack, redirect_stdout
from pathlib import Path
from unittest.mock import Mock, patch

from test_helper import HELPER as h

CONFIG = "[Interface]\nAddress = 10.0.0.2/32\n[Peer]\nAllowedIPs = 0.0.0.0/0\n"


class HardeningTests(unittest.TestCase):
    def test_lock_contention_is_bounded(self):
        with h.operation_lock():
            with h.operation_lock(nonblocking=True) as acquired:
                self.assertFalse(acquired)
            with self.assertRaisesRegex(RuntimeError, "lock timed out"):
                with h.operation_lock(timeout=0.02):
                    self.fail("Contended lock unexpectedly acquired")
        with h.operation_lock() as acquired:
            self.assertTrue(acquired)

    def test_stop_wait_budget_covers_startup_and_cleanup(self):
        with patch.object(h, "checked_profile", return_value=Path("/test.conf")), \
             patch.object(h, "operation_lock") as lock, \
             patch.object(h, "active_interfaces", return_value={"test"}), \
             patch.object(h, "run") as run:
            h.service_down("test")
        lock.assert_called_once_with(name="engine", timeout=120)
        self.assertEqual(run.call_args.kwargs["timeout"], 35)
        unit = Path(__file__).resolve().parents[1] / "systemd/amneziawg@.service"
        self.assertIn("TimeoutStopSec=180", unit.read_text())

    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.directory = Path(self.stack.enter_context(tempfile.TemporaryDirectory()))
        for key, value in {"CONFIG_DIR": self.directory / "configs", "STATE_DIR": self.directory / "state",
                           "TRASH_DIR": self.directory / "configs/.trash"}.items():
            self.stack.enter_context(patch.object(h, key, value))
        h.ensure_dirs()

    def test_internal_whitespace_cannot_bypass_engine_checks(self):
        for key in ("Fw Mark", "Fw\tMark", "F w M a r k"):
            with self.assertRaises(RuntimeError):
                h.validate_config(CONFIG.replace("[Peer]", key + " = 100\n[Peer]"))
        for key in ("Allowed IPs", "Allowed\tIPs"):
            with self.assertRaises(RuntimeError):
                h.validate_config(CONFIG.replace("AllowedIPs", key))

    def test_metadata_rejects_disguised_full_tunnel(self):
        path = h.profile_path("demo")
        path.write_text(CONFIG.replace("AllowedIPs", "Allowed IPs"))
        with self.assertRaises(RuntimeError):
            h.read_profile_metadata(path)

    def test_rejects_wrong_section_and_unknown_directive(self):
        for line in ("MTU = 1400", "Something = abc", "Post Up = bad"):
            with self.assertRaises(RuntimeError):
                h.validate_config(CONFIG + line + "\n")

    def test_rejects_invalid_key_and_dns_globs(self):
        for line in ("PrivateKey = invalid", "DNS = *", "DNS = $(id)"):
            with self.assertRaises(RuntimeError):
                h.validate_config(CONFIG.replace("[Peer]", line + "\n[Peer]"))

    def test_bounded_read_rejects_fifo_link_and_large_file(self):
        fifo = self.directory / "fifo"
        os.mkfifo(fifo)
        large = self.directory / "large"
        large.write_bytes(b"x" * (h.MAX_CONFIG_BYTES + 1))
        link = self.directory / "link"
        link.symlink_to(large)
        for path in (fifo, large, link, self.directory):
            with self.assertRaises(RuntimeError):
                h.read_regular(path)

    def test_private_read_rejects_nonroot_owner_and_loose_mode(self):
        path = self.directory / "profile"
        path.write_text(CONFIG)
        info = Mock(st_mode=0o100644, st_size=len(CONFIG), st_uid=0)
        with patch.object(h.os, "fstat", return_value=info), self.assertRaises(RuntimeError):
            h.read_regular(path, private=True)
        info.st_mode, info.st_uid = 0o100600, 1000
        with patch.object(h.os, "fstat", return_value=info), self.assertRaises(RuntimeError):
            h.read_regular(path, private=True)

    def test_bad_profile_does_not_break_other_rows(self):
        service = {"ActiveState": "inactive", "UnitFileState": "disabled"}
        with patch.object(h, "profile_names", return_value=["bad", "good"]), \
             patch.object(h, "active_interfaces", return_value=set()), \
             patch.object(h, "services_snapshot", return_value={h.unit_name(n): service for n in ("bad", "good")}), \
             patch.object(h, "checked_profile", side_effect=[RuntimeError("bad"), h.profile_path("good")]), \
             patch.object(h, "profile_record", return_value={"name": "good", "health": "disconnected"}), \
             redirect_stdout(io.StringIO()) as output:
            h.cmd_list()
        records = json.loads(output.getvalue())
        self.assertEqual([p["health"] for p in records], ["error", "disconnected"])

    def test_service_snapshot_uses_one_subprocess(self):
        output = "Id=amneziawg@one.service\nActiveState=active\n\nId=amneziawg@two.service\nActiveState=inactive\n"
        with patch.object(h, "run", return_value=output) as run:
            result = h.services_snapshot(["one", "two"])
        run.assert_called_once()
        self.assertEqual(result[h.unit_name("two")]["ActiveState"], "inactive")

    def test_slow_request_has_absolute_deadline(self):
        connection = Mock()
        connection.recv.return_value = b"x"
        with patch.object(h, "peer_is_authorized", return_value=True), \
             patch.object(h.time, "monotonic", side_effect=[0, 1, 6]):
            h.serve_connection(connection)
        self.assertEqual(connection.recv.call_count, 1)
        self.assertFalse(json.loads(connection.sendall.call_args.args[0])["ok"])

    def test_directory_symlink_is_rejected_before_creating_children(self):
        outside = self.directory / "outside"
        outside.mkdir()
        link = self.directory / "link"
        link.symlink_to(outside, target_is_directory=True)
        with patch.object(h, "CONFIG_DIR", link), patch.object(h, "TRASH_DIR", link / ".trash"):
            with self.assertRaises(RuntimeError):
                h.ensure_dirs()
        self.assertFalse((outside / ".trash").exists())
