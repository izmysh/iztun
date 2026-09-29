#!/usr/bin/python3
"""GTK regressions using synthetic profiles and local test sockets, without VPN/root.

Run in a desktop session or with xvfb-run -a. Defaults to the installed GUI;
use --source src/amneziawg-linux-gui to check a workspace without installing it.
"""

import argparse
from contextlib import contextmanager
import importlib.util
from importlib.machinery import SourceFileLoader
import json
import os
import pwd
from pathlib import Path
import socket
import stat
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--source", default="/usr/bin/amneziawg-linux-gui")
options, test_args = parser.parse_known_args()
loader = SourceFileLoader("gui_check", options.source)
spec = importlib.util.spec_from_loader(loader.name, loader)
gui = importlib.util.module_from_spec(spec)
loader.exec_module(gui)
Gtk, GLib = gui.Gtk, gui.GLib
from gi.repository import Gio


def children(widget):
    yield widget
    if isinstance(widget, Gtk.Container):
        for child in widget.get_children():
            yield from children(child)


def pump_until(predicate, timeout=4):
    deadline = time.monotonic() + timeout
    context = GLib.MainContext.default()
    while time.monotonic() < deadline:
        for _ in range(100):
            if not context.pending():
                break
            context.iteration(False)
        if predicate():
            return
        time.sleep(0.002)
    raise AssertionError("Timed out waiting for GTK/worker completion")


def profile(**changes):
    record = dict(name="test", label="Test", active=False, enabled=False,
                  protocol="AWG 2", health="disconnected", full_tunnel=True,
                  rx=0, tx=0, latest_handshake=0, last_error="")
    record.update(changes)
    return record


class GuiTests(unittest.TestCase):
    def setUp(self):
        self.app = gui.AmneziaWGApplication()
        self.app.set_application_id("io.github.amneziawg_linux_gui.UICheck")
        self.app.set_flags(Gio.ApplicationFlags.NON_UNIQUE)
        self.assertTrue(self.app.register(None))
        self.app.build_window()
        self.record, self.calls, self.gates, self.callback_errors = profile(), [], [], []
        self.hook = patch.object(sys, "excepthook", lambda *error: self.callback_errors.append(error))
        self.hook.start()
        self.app.helper = self.helper
        self.app.render_profiles([dict(self.record)])
        self.app.window.show_all()

    def tearDown(self):
        for gate in self.gates:
            gate.set()
        self.app.stop_background_work()
        pump_until(lambda: not self.app.pending_calls)
        self.app.window.destroy()
        GLib.idle_add(lambda: self.app.quit() or False)
        self.app.run([])
        self.hook.stop()
        self.assertFalse(self.callback_errors, f"Unhandled GTK callback errors: {self.callback_errors}")

    def helper(self, *args):
        self.calls.append(args)
        if args[0] == "list":
            return json.dumps([self.record])
        if args[0] == "read-config":
            return json.dumps({"text": "# Synthetic config\n", "revision": "test-revision"})
        if args[0] == "rename":
            self.record["label"] = args[2]
        if args[0] == "autostart":
            self.record["enabled"] = args[2] == "on"
        return "OK"

    def gate(self):
        gate = threading.Event()
        self.gates.append(gate)
        return gate

    def settle(self):
        pump_until(lambda: not self.app.pending_calls and not self.app.busy and not self.app.refreshing)

    def editor(self):
        self.app.edit_profile(None, "test")
        pump_until(lambda: self.app.editor is not None)
        dialog = self.app.editor
        view = next(w for w in children(dialog) if isinstance(w, Gtk.TextView))
        return dialog, view, view.get_buffer()

    def test_layout_and_in_place_updates(self):
        app = self.app
        self.assertEqual(gui.APP_VERSION, "0.3.0")
        self.assertEqual(app.window.get_title(), "IZtun")
        self.assertEqual(app.window.get_titlebar().get_title(), "IZtun")
        self.assertFalse(app.window.get_titlebar().get_subtitle())
        self.assertEqual(app.window.get_default_size(), (760, 500))
        row = app.profile_rows["test"]
        header = row.get_header()
        self.assertIsInstance(row.get_child(), Gtk.Grid)
        self.assertFalse(row.awg_detail.get_visible())
        more = next(w for w in children(row) if isinstance(w, Gtk.MenuButton))
        labels = [w.get_label() for w in more.get_popup().get_children() if isinstance(w, Gtk.MenuItem)]
        self.assertIn("Rename…", labels)
        self.assertIn("Edit configuration…", labels)
        self.assertEqual(app.notice.get_xalign(), 1)
        self.assertEqual(app.traffic.get_xalign(), 1)
        for index in range(100):
            app.render_profiles([profile(active=True, enabled=True, health="connected", rx=index * 100,
                                         label="<Работа & home>")])
        self.assertIs(app.profile_rows["test"], row)
        self.assertIs(row.get_header(), header)
        self.assertIn("<Работа & home>", row.awg_title.get_text())
        self.assertEqual(row.awg_action.get_label(), "Disconnect")
        self.assertFalse(row.awg_edit.get_sensitive())
        self.assertTrue(row.awg_switch.get_active())
        self.assertFalse(self.calls, "Rendering must not send mutations")
        app.render_profiles([profile(last_error="generic error")])
        self.assertIn("Repair", row.awg_detail.get_text())
        self.assertEqual(row.awg_detail.get_tooltip_text(), row.awg_detail.get_text())
        self.assertTrue(row.awg_detail.get_visible())
        self.assertEqual(row.awg_action.get_label(), "Connect")
        self.assertTrue(row.awg_edit.get_sensitive())
        self.assertFalse(any(isinstance(w, Gtk.Label) and ("Connection health is verified" in w.get_text()
                             or "Automatic recovery runs" in w.get_text() or w.get_text() == "Profiles")
                             for w in children(app.window)))

    def test_invalid_profile_fallback_and_validation(self):
        invalid = profile(protocol="Invalid config", health="error", last_error="Invalid profile")
        self.app.render_profiles(gui.parse_profiles(json.dumps([invalid])))
        self.assertIn("Invalid config", self.app.profile_rows["test"].awg_title.get_text())
        self.assertEqual(self.app.profile_rows["test"].awg_state.get_text(), "Connection problem")
        for records in ({}, [None], [profile(), profile()], [profile(active=1)],
                        [profile(rx=-1)], [profile(tx="NaN")], [profile(label=[])],
                        [profile(name="../bad")], [profile()] * (gui.MAX_PROFILES + 1)):
            with self.subTest(records=str(records)[:80]), self.assertRaises(ValueError):
                gui.parse_profiles(json.dumps(records))

    def test_footer_rates_progress_and_errors(self):
        app = self.app
        app.previous_traffic.clear()
        with patch.object(gui.time, "monotonic", return_value=100):
            app.render_profiles([profile(active=True, health="connected", rx=1024, tx=512)])
        with patch.object(gui.time, "monotonic", return_value=102):
            app.render_profiles([profile(active=True, health="connected", rx=2048, tx=1024)])
        self.assertIn("Connected", app.notice.get_text())
        self.assertIn("512 B/s", app.traffic.get_text())
        self.assertIn("2.0 KiB", app.traffic.get_text())
        app.operation = ("up", "test")
        app.update_footer()
        self.assertIn("Connecting", app.notice.get_text())
        self.assertIn("Waiting for handshake", app.notice.get_text())
        app.poll_error = "Connection status unavailable"
        app.update_footer()
        self.assertEqual(app.notice.get_text(), app.poll_error)
        self.assertFalse(app.traffic.get_text())
        app.operation = None
        app.render_profiles([profile()])
        self.assertFalse(app.notice.get_text())
        self.assertFalse(app.traffic.get_text())
        app.render_profiles([profile(active=True, rx=999999)])
        self.assertEqual(app.profiles[0]["rx_rate"], 0, "Reconnect must reset the rate baseline")
        app.render_profiles([])
        self.assertFalse(app.previous_traffic)
        self.assertEqual(app.stack.get_visible_child_name(), "empty")

    def check_stale_poll(self, error=False):
        gate, started = self.gate(), threading.Event()
        poll_count, rendered = 0, []
        render = self.app.render_profiles

        def track(records):
            rendered.append(records[0]["label"])
            return render(records)

        def helper(*args):
            nonlocal poll_count
            if args[0] == "list":
                poll_count += 1
                if poll_count == 1:
                    started.set()
                    if not gate.wait(4):
                        raise RuntimeError("Test gate timed out")
                    if error:
                        raise RuntimeError("Obsolete poll error")
                    return json.dumps([profile(label="OLD")])
                return json.dumps([profile(label="NEW")])
            return self.helper(*args)

        self.app.helper, self.app.render_profiles = helper, track
        self.app.refresh()
        pump_until(started.is_set)
        self.app.run_action(["rename", "test", "NEW"])
        pump_until(lambda: not self.app.busy)
        self.assertTrue(self.app.refresh_pending)
        for _ in range(30):
            self.app.refresh()
        self.assertEqual(poll_count, 1)
        gate.set()
        self.settle()
        self.assertEqual(rendered, ["NEW"])
        self.assertEqual(poll_count, 2)
        self.assertFalse(self.app.poll_error)
        self.assertFalse(self.app.error_visible)

    def test_stale_poll_success_after_action(self):
        self.check_stale_poll()

    def test_stale_poll_error_after_action(self):
        self.check_stale_poll(error=True)

    def test_bounded_lanes_and_polling_during_action(self):
        gate, started = self.gate(), threading.Event()

        def helper(*args):
            if args[0] == "up":
                started.set()
                if not gate.wait(4):
                    raise RuntimeError("Test gate timed out")
            return self.helper(*args)

        self.app.helper = helper
        self.assertTrue(self.app.run_action(["up", "test"]))
        pump_until(started.is_set)
        self.assertFalse(self.app.run_action(["down", "test"]))
        self.app.import_profile()
        self.app.edit_profile(None, "test")
        self.assertIsNone(self.app.dialog)
        self.assertTrue(all(not b.get_sensitive() for b in self.app.import_buttons))
        self.app.refresh()
        pump_until(lambda: not self.app.refreshing)
        self.assertTrue(self.app.busy)
        self.assertIn(("list",), self.calls)
        self.assertTrue(self.app.async_call(lambda: gate.wait(4)))
        for _ in range(100):
            self.assertFalse(self.app.async_call(lambda: "unexpected"))
        self.assertLessEqual(len(self.app.pending_calls), 3)
        tick = []
        GLib.idle_add(lambda: tick.append(True) and False)
        pump_until(lambda: bool(tick))
        gate.set()
        self.settle()
        self.assertTrue(self.app.listbox.get_sensitive())

    def test_completed_worker_keeps_lane_until_delivery(self):
        completed = threading.Event()
        self.app.async_call(lambda: completed.set())
        self.assertTrue(completed.wait(2))
        self.assertFalse(self.app.async_call(lambda: None))
        self.settle()
        self.assertTrue(self.app.async_call(lambda: None))
        self.settle()

    def test_hidden_poll_throttle_and_error_recovery(self):
        self.app.window.hide()
        self.app.last_refresh = time.monotonic()
        self.app.refresh(timer=True)
        self.assertFalse(self.calls)
        self.app.last_refresh -= 16
        self.app.refresh(timer=True)
        self.settle()
        self.assertEqual(self.calls, [("list",)])
        self.app.helper = lambda *_: "not JSON"
        self.app.refresh()
        self.settle()
        self.assertTrue(self.app.poll_error)
        self.assertFalse(self.app.error_visible)
        self.app.helper = self.helper
        self.app.refresh()
        self.settle()
        self.assertFalse(self.app.poll_error)

    def test_rename_and_delete_are_modal_and_nonblocking(self):
        self.app.rename_profile(None, self.record)
        dialog = self.app.dialog
        self.assertTrue(dialog.get_modal())
        self.app.import_profile()
        self.assertIs(self.app.dialog, dialog)
        entry = next(w for w in children(dialog) if isinstance(w, Gtk.Entry))
        entry.set_text("Работа")
        dialog.response(Gtk.ResponseType.OK)
        self.settle()
        self.assertEqual(self.record["label"], "Работа")
        self.assertIsNone(self.app.interaction)
        self.app.delete_profile(None, "test")
        self.assertTrue(self.app.dialog.get_modal())
        self.app.dialog.response(Gtk.ResponseType.CANCEL)
        self.assertNotIn(("delete", "test"), self.calls)
        self.app.delete_profile(None, "test")
        self.app.dialog.response(Gtk.ResponseType.OK)
        self.settle()
        self.assertIn(("delete", "test"), self.calls)

    def test_editor_load_deduplicated_and_cancel_clears_text(self):
        gate = self.gate()

        def helper(*args):
            if args[0] == "read-config" and not gate.wait(4):
                raise RuntimeError("Test gate timed out")
            return self.helper(*args)

        self.app.helper = helper
        for _ in range(30):
            self.app.edit_profile(None, "test")
        self.app.import_profile()
        self.assertFalse(self.app.run_action(["up", "test"]))
        self.assertEqual(self.app.pending_calls, {"aux"})
        gate.set()
        pump_until(lambda: self.app.editor is not None)
        dialog = self.app.editor
        buffer = next(w for w in children(dialog) if isinstance(w, Gtk.TextView)).get_buffer()
        self.assertEqual(self.calls.count(("read-config", "test")), 1)
        dialog.response(Gtk.ResponseType.CANCEL)
        self.assertEqual(buffer.get_char_count(), 0)
        self.assertIsNone(self.app.editor)
        self.assertIsNone(self.app.interaction)

    def test_editor_save_failure_retry_and_cancel_while_saving(self):
        dialog, view, buffer = self.editor()
        self.assertTrue(view.get_monospace())
        buffer.set_text("# Edited synthetic configuration\n")
        gate = self.gate()

        def fail_save(*args):
            if args[0] == "save-config":
                self.calls.append(args)
                if not gate.wait(4):
                    raise RuntimeError("Test gate timed out")
                raise RuntimeError("Revision changed")
            return self.helper(*args)

        self.app.helper = fail_save
        dialog.response(Gtk.ResponseType.OK)
        self.assertTrue(self.app.busy)
        dialog.response(Gtk.ResponseType.CANCEL)
        dialog.response(Gtk.ResponseType.OK)
        self.assertIs(self.app.editor, dialog)
        self.assertFalse(view.get_editable())
        self.assertFalse(dialog.get_deletable())
        gate.set()
        self.settle()
        self.assertEqual(sum(c[0] == "save-config" for c in self.calls), 1)
        self.assertTrue(view.get_editable())
        self.assertGreater(buffer.get_char_count(), 0)
        self.assertTrue(self.app.error_dialog.get_modal())
        self.assertIs(self.app.error_dialog.get_transient_for(), dialog)
        self.app.error_dialog.response(Gtk.ResponseType.CLOSE)
        self.app.helper = self.helper
        dialog.response(Gtk.ResponseType.OK)
        self.settle()
        saved = [c for c in self.calls if c[0] == "save-config"][-1]
        self.assertEqual(json.loads(saved[2]), {"text": "# Edited synthetic configuration\n", "revision": "test-revision"})
        self.assertEqual(buffer.get_char_count(), 0)
        self.assertIsNone(self.app.editor)
        self.assertIsNone(self.app.interaction)

    def test_editor_oversize_and_load_error(self):
        dialog, _view, buffer = self.editor()
        buffer.set_text("я" * 32769)
        dialog.response(Gtk.ResponseType.OK)
        self.assertFalse(any(c[0] == "save-config" for c in self.calls))
        self.assertIn("64 KiB", self.app.notice.get_text())
        self.app.error_dialog.response(Gtk.ResponseType.CLOSE)
        dialog.response(Gtk.ResponseType.CANCEL)
        self.app.helper = lambda *_: json.dumps({"text": [], "revision": "r"})
        self.app.edit_profile(None, "test")
        self.settle()
        self.assertIsNone(self.app.editor)
        self.assertIsNone(self.app.interaction)
        self.assertTrue(self.app.error_visible)

    def test_import_chooser_and_name_ownership(self):
        self.app.import_profile()
        chooser = self.app.dialog
        self.assertTrue(chooser.get_modal())
        pump_until(lambda: chooser.get_current_folder() == pwd.getpwuid(os.getuid()).pw_dir)
        self.app.edit_profile(None, "test")
        self.assertIs(self.app.dialog, chooser)
        chooser.response(Gtk.ResponseType.CANCEL)
        self.assertIsNone(self.app.interaction)
        owner = self.app.begin_interaction()
        self.app.name_import(owner, "/tmp/work.conf", "# Synthetic import\n")
        dialog = self.app.dialog
        self.assertTrue(dialog.get_modal())
        self.assertFalse(self.app.run_action(["up", "test"]))
        entry = next(w for w in children(dialog) if isinstance(w, Gtk.Entry))
        entry.set_text("work")
        dialog.response(Gtk.ResponseType.OK)
        self.assertEqual(self.app.operation, ("import", None))
        self.settle()
        self.assertIn(("import", "# Synthetic import\n", "work"), self.calls)

    def test_autostart_and_action_failure_restore_controls(self):
        switch = self.app.profile_rows["test"].awg_switch
        switch.emit("state-set", True)
        self.settle()
        self.assertTrue(switch.get_active())
        self.assertEqual(self.calls.count(("autostart", "test", "on")), 1)

        def fail(*args):
            if args[0] != "list":
                raise RuntimeError("Synthetic failure")
            return self.helper(*args)

        self.app.helper = fail
        self.app.run_action(["up", "test"])
        self.settle()
        self.assertFalse(self.app.busy)
        self.assertFalse(self.app.listbox.get_sensitive())
        self.app.show_error("Second failure")
        errors = [w for w in Gtk.Window.list_toplevels() if isinstance(w, Gtk.MessageDialog) and w.get_visible()]
        self.assertEqual(len(errors), 1)
        self.app.error_dialog.response(Gtk.ResponseType.CLOSE)
        self.assertTrue(self.app.listbox.get_sensitive())

    def test_status_and_diagnostics_dialogs(self):
        self.app.show_status(None, "test")
        pump_until(lambda: self.app.dialog is not None)
        self.assertTrue(self.app.dialog.get_modal())
        self.app.dialog.response(Gtk.ResponseType.CLOSE)
        self.app.export_diagnostics(None, "test")
        pump_until(lambda: self.app.dialog is not None)
        self.assertTrue(self.app.dialog.get_modal())
        pump_until(lambda: self.app.dialog.get_current_folder() == pwd.getpwuid(os.getuid()).pw_dir)
        self.app.dialog.response(Gtk.ResponseType.CANCEL)
        self.assertIsNone(self.app.interaction)

    def test_about_button_dialog_and_link_without_navigation(self):
        button = next(w for w in children(self.app.window.get_titlebar())
                      if isinstance(w, Gtk.Button) and w.get_tooltip_text() == "About IZtun")
        self.assertEqual(button.get_image().get_icon_name()[0], "help-about-symbolic")
        button.clicked()
        dialog = self.app.dialog
        self.assertTrue(dialog.get_modal())
        labels = [w.get_text() for w in children(dialog) if isinstance(w, Gtk.Label)]
        self.assertIn("IZtun 0.3.0", labels)
        self.assertIn("IZtun is a lightweight GUI frontend for AmneziaWG-GO on ARM64 Linux systems.", labels)
        self.assertIn("Developed by IZMYSH", labels)
        link = next(w for w in children(dialog) if isinstance(w, Gtk.LinkButton))
        self.assertEqual(link.get_uri(), "https://github.com/izmysh/iztun")
        self.assertTrue(link.get_can_focus())
        self.assertIsNotNone(link.get_image())
        dialog.response(Gtk.ResponseType.CLOSE)
        self.assertIsNone(self.app.interaction)

    def test_import_file_bounds_and_special_files(self):
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / "test.conf"
            config.write_bytes(b"# config\n")
            self.assertEqual(gui.read_import(str(config)), "# config\n")
            config.write_bytes(b"x" * gui.MAX_CONFIG_BYTES)
            self.assertEqual(len(gui.read_import(str(config))), gui.MAX_CONFIG_BYTES)
            config.write_bytes(b"x" * (gui.MAX_CONFIG_BYTES + 1))
            with self.assertRaisesRegex(ValueError, "64 KiB"):
                gui.read_import(str(config))
            config.write_bytes(b"\xff")
            with self.assertRaises(UnicodeError):
                gui.read_import(str(config))
            fifo = Path(directory) / "fifo.conf"
            os.mkfifo(fifo)
            start = time.monotonic()
            with self.assertRaisesRegex(ValueError, "regular"):
                gui.read_import(str(fifo))
            self.assertLess(time.monotonic() - start, 0.5)
            with self.assertRaises(ValueError):
                gui.read_import(str(Path(directory) / "wrong.txt"))

    def test_diagnostics_private_atomic_write_and_cleanup(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "report.txt"
            target.write_text("old")
            target.chmod(0o644)
            gui.write_diagnostics(str(target), "new")
            self.assertEqual(target.read_text(), "new\n")
            self.assertEqual(stat.S_IMODE(target.stat().st_mode), 0o600)
            with patch.object(gui.os, "replace", side_effect=OSError("Synthetic write failure")):
                with self.assertRaises(OSError):
                    gui.write_diagnostics(str(target), "incomplete")
            self.assertEqual(target.read_text(), "new\n")
            self.assertEqual(list(Path(directory).iterdir()), [target])
            link = Path(directory) / "link.txt"
            link.symlink_to(target)
            with self.assertRaises(ValueError):
                gui.write_diagnostics(str(link), "unsafe")
            fifo = Path(directory) / "fifo.txt"
            os.mkfifo(fifo)
            with self.assertRaises(ValueError):
                gui.write_diagnostics(str(fifo), "unsafe")

    @contextmanager
    def server(self, respond):
        errors, requests = [], []
        with tempfile.TemporaryDirectory() as directory:
            address = str(Path(directory) / "helper.sock")
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as listener:
                listener.bind(address)
                listener.listen(1)
                listener.settimeout(3)

                def serve():
                    try:
                        connection, _ = listener.accept()
                        with connection:
                            connection.settimeout(3)
                            request = bytearray()
                            while True:
                                chunk = connection.recv(65536)
                                if not chunk:
                                    break
                                request.extend(chunk)
                            requests.append(json.loads(request))
                            respond(connection)
                    except (BrokenPipeError, ConnectionResetError):
                        pass
                    except Exception as exc:
                        errors.append(exc)

                thread = threading.Thread(target=serve, daemon=True)
                thread.start()
                try:
                    with patch.object(gui, "HELPER_SOCKET", address):
                        yield requests
                finally:
                    thread.join(4)
                    self.assertFalse(thread.is_alive(), "Test socket thread did not stop")
                    self.assertFalse(errors, str(errors))

    def real_helper(self, *args):
        return gui.AmneziaWGApplication.helper(self.app, *args)

    def test_socket_response_validation_and_size_limit(self):
        with self.server(lambda client: client.sendall(b'{"ok": true, "output": "hello"}\n')) as requests:
            self.assertEqual(self.real_helper("status", "test"), "hello")
        self.assertEqual(requests, [{"args": ["status", "test"]}])
        for payload in (b"", b"[]", b"null", b"\xff", b'{"ok": 1}',
                        b'{"ok": true, "output": {}}', b'{"ok": false, "error": []}'):
            with self.subTest(payload=payload):
                with self.server(lambda client: client.sendall(payload)):
                    with self.assertRaisesRegex(RuntimeError, "Malformed"):
                        self.real_helper("list")
        with patch.object(gui, "MAX_RESPONSE_BYTES", 64):
            with self.server(lambda client: client.sendall(b"x" * 65)):
                with self.assertRaisesRegex(RuntimeError, "too large"):
                    self.real_helper("list")
        with self.server(lambda client: client.sendall(b'{"ok": false, "error": "Denied"}')):
            with self.assertRaisesRegex(RuntimeError, "Denied"):
                self.real_helper("list")
        with patch.object(gui.socket, "socket", side_effect=AssertionError("No socket should be opened")):
            with self.assertRaisesRegex(ValueError, "too large"):
                self.real_helper("import", "x" * gui.MAX_REQUEST_BYTES, "test")

    def test_socket_total_deadline_even_with_drip_feed(self):
        def drip(client):
            for _ in range(30):
                client.sendall(b" ")
                time.sleep(0.02)

        with patch.dict(gui.READ_TIMEOUTS, {"list": 0.12}):
            with self.server(drip):
                start = time.monotonic()
                with self.assertRaisesRegex(RuntimeError, "timed out"):
                    self.real_helper("list")
                self.assertLess(time.monotonic() - start, 0.5)
        with patch.object(gui, "ACTION_TIMEOUT", 0.12):
            with self.server(drip):
                with self.assertRaisesRegex(RuntimeError, "may still finish"):
                    self.real_helper("up", "test")

    def test_shutdown_closes_socket_and_suppresses_callbacks(self):
        connected, release = threading.Event(), self.gate()

        def wait_for_close(client):
            connected.set()
            release.wait(3)
            client.sendall(b'{"ok": true, "output": "late"}')

        callbacks = []
        with self.server(wait_for_close):
            self.app.async_call(lambda: self.real_helper("status", "test"),
                                lambda result: callbacks.append(result), lambda: callbacks.append("finished"))
            pump_until(connected.is_set)
            self.app.refresh_timer = GLib.timeout_add_seconds(5, lambda: True)
            self.app.stop_background_work()
            pump_until(lambda: not self.app.pending_calls)
            release.set()
        self.assertFalse(callbacks)
        self.assertFalse(self.app.sockets)
        self.assertIsNone(self.app.refresh_timer)
        self.assertFalse(self.app.refresh())

    def test_quit_during_editor_load_does_not_open_dialog(self):
        gate = self.gate()

        def helper(*args):
            if not gate.wait(4):
                raise RuntimeError("Test gate timed out")
            return self.helper(*args)

        self.app.helper = helper
        self.app.edit_profile(None, "test")
        self.app.stop_background_work()
        gate.set()
        self.settle()
        self.assertIsNone(self.app.editor)
        self.assertIsNone(self.app.dialog)


if __name__ == "__main__":
    if not Gtk.init_check()[0]:
        raise SystemExit("GTK display unavailable. Run with xvfb-run -a scripts/verify-gui.py.")
    unittest.main(argv=[sys.argv[0], *test_args], verbosity=2)
