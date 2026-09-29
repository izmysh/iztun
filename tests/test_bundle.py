import contextlib
import hashlib
import importlib.util
import io
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch

path = Path(__file__).resolve().parents[1] / "packaging/source-bundle.py"
spec = importlib.util.spec_from_file_location("bundle", path)
bundle = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bundle)


class BundleTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        for directory in bundle.DIRECTORIES:
            (self.root / directory).mkdir(parents=True)
        (self.root / "VERSION").write_text("0.3.0\n")
        (self.root / "sysusers.d/group.conf").write_text("g amneziawg -\n")
        self.hook = patch.object(bundle, "ROOT", self.root)
        self.hook.start()
        self.addCleanup(self.hook.stop)

    def export(self):
        with contextlib.redirect_stdout(io.StringIO()):
            bundle.main()
        return self.root / "dist/iztun-0.3.0-source.tar.gz"

    def test_manifest_and_allowlist(self):
        (self.root / "private.conf").write_text("not for release")
        (self.root / "src/private.conf").write_text("not for release")
        (self.root / "src/cache.pyc").write_bytes(b"cache")
        output = self.export()
        with tarfile.open(output) as archive:
            self.assertEqual(set(archive.getnames()), {
                "iztun-0.3.0/VERSION", "iztun-0.3.0/sysusers.d/group.conf",
                "iztun-0.3.0/SOURCE-MANIFEST.sha256"})
            manifest = archive.extractfile("iztun-0.3.0/SOURCE-MANIFEST.sha256").read().decode()
            for line in manifest.splitlines():
                digest, name = line.split("  ", 1)
                self.assertEqual(hashlib.sha256(archive.extractfile("iztun-0.3.0/" + name).read()).hexdigest(), digest)

    def test_rejects_secrets_and_binary_even_with_source_extension(self):
        for data in (b"PrivateKey = " + b"A" * 43 + b"=\n", b"\x7fELFbinary"):
            with self.subTest(data=data[:12]):
                (self.root / "src/example.py").write_bytes(data)
                with self.assertRaisesRegex(RuntimeError, "Secret or compiled binary"):
                    self.export()
                self.assertFalse((self.root / "dist/iztun-0.3.0-source.tar.tmp").exists())

    def test_rejects_unreviewed_links(self):
        (self.root / "src/link").symlink_to(self.root / "VERSION")
        with self.assertRaisesRegex(RuntimeError, "source symlink"):
            self.export()

    def test_versions_match(self):
        project = path.parents[1]
        version = (project / "VERSION").read_text().strip()
        self.assertIn(f'APP_VERSION = "{version}"', (project / "src/amneziawg-linux-gui").read_text())
