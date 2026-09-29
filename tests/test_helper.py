import importlib.util
from importlib.machinery import SourceFileLoader
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
HELPER_PATH = PROJECT_ROOT / "src" / "amneziawg-linux-gui-helper"
LOADER = SourceFileLoader("amneziawg_linux_gui_helper", str(HELPER_PATH))
SPEC = importlib.util.spec_from_loader(LOADER.name, LOADER)
HELPER = importlib.util.module_from_spec(SPEC)
LOADER.exec_module(HELPER)


class ProfileNameTests(unittest.TestCase):
    def test_accepts_linux_interface_name(self):
        self.assertEqual(HELPER.profile_name("office-awg"), "office-awg")

    def test_rejects_path_traversal(self):
        with self.assertRaises(SystemExit):
            HELPER.profile_name("../../secret")

    def test_rejects_names_longer_than_interface_limit(self):
        with self.assertRaises(SystemExit):
            HELPER.profile_name("a" * 16)


class ProtocolTests(unittest.TestCase):
    def hint(self, text):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "profile.conf"
            path.write_text(text, encoding="utf-8")
            return HELPER.protocol_hint(path)

    def test_detects_awg_31(self):
        self.assertEqual(self.hint("[Interface]\nRandomTrailers = on\n"), "AWG 3.1")

    def test_detects_awg_3(self):
        self.assertEqual(self.hint("[Interface]\nHeaderProtectionKey = abc\n"), "AWG 3")

    def test_detects_awg_2(self):
        self.assertEqual(self.hint("[Interface]\nI1 = <r 2>\n"), "AWG 2")

    def test_falls_back_to_awg(self):
        self.assertEqual(self.hint("[Interface]\nAddress = 10.0.0.2/32\n"), "AWG")


class ImportSafetyTests(unittest.TestCase):
    def test_rejects_shell_hooks(self):
        config = "[Interface]\nPostUp = touch /tmp/owned\n[Peer]\nPublicKey = value\n"
        self.assertIsNotNone(HELPER.FORBIDDEN.search(config))

    def test_accepts_normal_client_profile(self):
        config = "[Interface]\nAddress = 10.0.0.2/32\n[Peer]\nAllowedIPs = 0.0.0.0/0\n"
        self.assertIsNone(HELPER.FORBIDDEN.search(config))


class MetadataTests(unittest.TestCase):
    def metadata(self, text):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "profile.conf"
            path.write_text(text, encoding="utf-8")
            return HELPER.read_profile_metadata(path)

    def test_detects_full_tunnel_without_returning_secrets(self):
        metadata = self.metadata(
            "[Interface]\nPrivateKey = AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=\n"
            "DNS = 1.1.1.1\n[Peer]\nAllowedIPs = 0.0.0.0/0, ::/0\nPersistentKeepalive = 25\n"
        )
        self.assertTrue(metadata["full_tunnel"])
        self.assertTrue(metadata["dns_configured"])
        self.assertTrue(metadata["persistent_keepalive"])
        self.assertEqual(metadata["peer_count"], 1)
        self.assertNotIn("PrivateKey", metadata)

    def test_split_tunnel_is_not_marked_full(self):
        metadata = self.metadata("[Interface]\n[Peer]\nAllowedIPs = 10.0.0.0/8, 192.168.0.0/16\n")
        self.assertFalse(metadata["full_tunnel"])


class HealthTests(unittest.TestCase):
    ACTIVE = {"ActiveState": "active"}
    INACTIVE = {"ActiveState": "inactive"}

    def test_fresh_handshake_is_connected(self):
        self.assertEqual(HELPER.classify_health(True, self.ACTIVE, 950, now=1000), "connected")

    def test_missing_handshake_is_waiting(self):
        self.assertEqual(HELPER.classify_health(True, self.ACTIVE, 0, now=1000), "waiting")

    def test_old_handshake_is_stale(self):
        self.assertEqual(HELPER.classify_health(True, self.ACTIVE, 700, now=1000), "stale")

    def test_interface_service_mismatch_is_error(self):
        self.assertEqual(HELPER.classify_health(True, self.INACTIVE, 950, now=1000), "error")

    def test_clean_inactive_profile_is_disconnected(self):
        self.assertEqual(HELPER.classify_health(False, self.INACTIVE, 0, now=1000), "disconnected")


class RedactionTests(unittest.TestCase):
    def test_removes_keys_tokens_and_addresses(self):
        report = HELPER.redact_text(
            "PrivateKey = secret\n"
            "token AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=\n"
            "endpoint 203.0.113.20:443 and 2001:db8::1\n"
        )
        self.assertNotIn("PrivateKey", report)
        self.assertNotIn("= secret", report)
        self.assertNotIn("AAAAAAAA", report)
        self.assertNotIn("203.0.113.20", report)
        self.assertNotIn("2001:db8::1", report)


if __name__ == "__main__":
    unittest.main()
