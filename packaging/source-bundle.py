#!/usr/bin/python3
"""Export only release sources, never the workspace, profiles or compiled files."""
import hashlib
import io
import re
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILES = ("README.md", "README.ru.md", "BUILDING.md", "BUILDING.ru.md", "PUBLISHING.md", "AUDIT.md", "SECURITY.md", "CHANGELOG.md", "LICENSE",
         "CONTRIBUTING.md", "ROADMAP.md", "THIRD_PARTY_NOTICES.md", "UPSTREAM_VERSIONS", "VERSION", "Makefile", ".gitignore")
DIRECTORIES = ("src", "data", "systemd", "sysusers.d", "tests", "scripts", "packaging", ".github",
               "upstream/amneziawg-go", "upstream/amneziawg-tools")
EXCLUDED = {".git", "__pycache__", "build", "dist", ".cache", "secrets", "credentials", "wg", "amneziawg-go"}
SUFFIXES = {".o", ".d", ".pyc", ".deb", ".log", ".conf", ".key", ".pem", ".previous", ".name"}
SECRET = re.compile(rb"(?m)^\s*(?:PrivateKey|PresharedKey|HeaderProtectionKey)\s*=\s*[A-Za-z0-9+/]{43}=|-----BEGIN (?:OPENSSH |RSA |EC )?PRIVATE KEY-----|gh[pousr]_[A-Za-z0-9]{30,}")
# Public upstream man-page examples, not credentials from this installation.
PUBLIC_EXAMPLES = {
    "upstream/amneziawg-tools/src/man/wg-quick.8": "08ccc5bfd62cfa53983e858c2420d33034282e554663b45726610e80da383ff4",
    "upstream/amneziawg-tools/src/man/wg.8": "8bb4e8714cdf7cb8ce1beaac6f7ea3e5a7f27f68962efce92e95bf438b9ac2a8",
}


def entries(root=None):
    root = ROOT if root is None else root
    for filename in FILES:
        path = root / filename
        if path.is_file():
            if path.is_symlink():
                raise RuntimeError(f"Unsafe source link: {filename}")
            yield path
    for directory in DIRECTORIES:
        base = root / directory
        if not base.is_dir() or base.is_symlink():
            raise RuntimeError(f"Missing or unsafe source directory: {directory}")
        for path in sorted(base.rglob("*")):
            relative = path.relative_to(base)
            if any(part in EXCLUDED for part in relative.parts) or (path.suffix in SUFFIXES and directory != "sysusers.d"):
                continue
            if path.is_symlink():
                if path.relative_to(root).as_posix() == "upstream/amneziawg-tools/src/wg-quick/awg":
                    continue
                raise RuntimeError(f"Review source symlink before release: {path.relative_to(root)}")
            if path.is_file():
                yield path


def main():
    version = (ROOT / "VERSION").read_text().strip()
    if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", version):
        raise RuntimeError("Invalid version")
    prefix = f"iztun-{version}"
    output = ROOT / "dist" / f"{prefix}-source.tar.gz"
    output.parent.mkdir(exist_ok=True)
    temporary = output.with_suffix(".tmp")
    manifest = []
    try:
        with tarfile.open(temporary, "w:gz") as archive:
            for path in entries():
                relative = path.relative_to(ROOT).as_posix()
                data = path.read_bytes()
                known_example = PUBLIC_EXAMPLES.get(relative) == hashlib.sha256(data).hexdigest()
                if (SECRET.search(data) and not known_example) or data.startswith(b"\x7fELF"):
                    raise RuntimeError(f"Secret or compiled binary in release input: {relative}")
                info = archive.gettarinfo(str(path), arcname=f"{prefix}/{relative}")
                info.uid = info.gid = 0
                info.uname = info.gname = ""
                info.mode = 0o755 if path.stat().st_mode & 0o111 else 0o644
                archive.addfile(info, io.BytesIO(data))
                manifest.append(f"{hashlib.sha256(data).hexdigest()}  {relative}\n")
            data = "".join(manifest).encode()
            info = tarfile.TarInfo(f"{prefix}/SOURCE-MANIFEST.sha256")
            info.size, info.mode = len(data), 0o644
            archive.addfile(info, io.BytesIO(data))
        temporary.replace(output)
    finally:
        temporary.unlink(missing_ok=True)
    checksum = hashlib.sha256(output.read_bytes()).hexdigest()
    output.with_name(output.name + ".sha256").write_text(f"{checksum}  {output.name}\n")
    print(output)


if __name__ == "__main__":
    main()
