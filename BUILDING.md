[🇬🇧 EN](BUILDING.md) | [🇷🇺 RU](BUILDING.ru.md)

[Back to README](README.md)

# Manual build on ARM64

Build as a regular user; use `sudo` only for installing dependencies or packages.
Keep your sources and compiler if you plan to build updates.

### 1. Install dependencies

```bash
sudo apt update
sudo apt install build-essential binutils pkg-config dpkg-dev git golang-go \
  python3 python3-gi gir1.2-gtk-3.0 gir1.2-ayatanaappindicator3-0.1 \
  iproute2 iptables resolvconf systemd
```

Use `openresolv` instead where appropriate; inspect package-manager changes before
replacing resolver integration. The build pins **Go 1.26.8**. A recent distro Go
downloads the selected toolchain automatically. If your distro Go cannot do this,
follow the [official Go installation instructions](https://go.dev/doc/install).

The source archive includes both upstream source trees, but not OS packages,
the Go compiler or its module cache. The first build needs Internet access;
Go dependency versions/checksums are pinned in `go.mod` and `go.sum`. This is not
an offline installation bundle.

### 2. Obtain sources

Recommended: download the complete source archive and checksum from the same release:

```bash
sha256sum -c iztun-0.3.0-source.tar.gz.sha256
tar -xzf iztun-0.3.0-source.tar.gz
cd iztun-0.3.0
sha256sum -c SOURCE-MANIFEST.sha256
```

This archive needs no Git initialization or submodule download. Alternatively:

```bash
git clone --recurse-submodules https://github.com/izmysh/iztun.git IZtun
cd IZtun
```

GitHub's automatic source ZIP may omit submodules. Prefer the complete release archive.

### 3. Compile AmneziaWG-GO, then the command-line tools

The supported target compiles both pinned upstream components in `build/`:

```bash
make engine
file build/engine/amneziawg-go build/engine/awg
build/engine/amneziawg-go --version
build/engine/awg --version
```

For clarity, here is the Go compilation step on its own, from the project root.
It creates a binary without installing it or connecting a VPN:

```bash
mkdir -p build/amneziawg-go-source build/engine
cp -a upstream/amneziawg-go/. build/amneziawg-go-source/
printf 'package main\n\nconst Version = "v3.1.20260828"\n' \
  > build/amneziawg-go-source/version.go
(
  cd build/amneziawg-go-source
  GOTOOLCHAIN=go1.26.8 CGO_ENABLED=0 go build -mod=readonly -trimpath \
    -buildvcs=false -o ../engine/amneziawg-go
)
```

`CGO_ENABLED=0` removes the Go engine's C runtime dependency. The separate `awg`
command is a C program and still needs libc. To build that component separately:

```bash
mkdir -p build/amneziawg-tools-source
cp -a upstream/amneziawg-tools/. build/amneziawg-tools-source/
make -C build/amneziawg-tools-source/src clean
CFLAGS='-O2 -D_FORTIFY_SOURCE=3 -fstack-protector-strong -fPIE' \
  LDFLAGS='-pie -Wl,-z,relro,-z,now' \
  make -C build/amneziawg-tools-source/src WIREGUARD_TOOLS_VERSION=3.1.20260812
cp build/amneziawg-tools-source/src/wg build/engine/awg
cp upstream/amneziawg-tools/src/wg-quick/linux.bash build/engine/awg-quick
chmod 755 build/engine/awg-quick
```

`make engine` performs these steps for you, including cleaning stale objects.
Exact upstream tags and commits are recorded in [UPSTREAM_VERSIONS](UPSTREAM_VERSIONS).
IZtun does not rewrite the upstream protocol or cryptography.

### 4. Check IZtun and build its package

The GUI/helper are Python programs: they need no separate ARM machine-code
compilation. These commands check Python syntax, run regressions and package the GUI with its engines:

```bash
make test
make deb
make source-bundle
```

`make deb` repeats tests and builds the engines to avoid stale binaries. Outputs:

```text
dist/amneziawg-linux-gui_0.3.0_arm64.deb
dist/amneziawg-linux-gui_0.3.0_arm64.deb.sha256
dist/iztun-0.3.0-source.tar.gz
dist/iztun-0.3.0-source.tar.gz.sha256
```

```bash
sudo apt install ./dist/amneziawg-linux-gui_0.3.0_arm64.deb
sudo amneziawg-linux-gui-setup-user "$USER"
# Sign out and back in, then:
iztun
```

`bash scripts/install-from-source.sh` is a convenience installer combining these
steps. Read it first: it installs system packages.

### 5. Optional contributor checks

```bash
# Check the shipped engine against the Go vulnerability database (Internet required).
make audit
# GUI tests use synthetic profiles; no real VPN connection is created.
sudo apt install xvfb xauth
xvfb-run -a python3 scripts/verify-gui.py --source src/amneziawg-linux-gui
```

`verify-installed.py` and `verify-profile-actions.py` also contain opt-in live
network tests. Read their help before running them; live checks connect/disconnect
tunnels. Do not use them during important remote work.

## Service checks

```bash
systemctl status amneziawg-linux-gui.socket
sudo systemctl enable --now amneziawg-linux-gui.socket
```

On systemd-networkd systems, network-change recovery also needs
`networkd-dispatcher` installed and enabled. See [AUDIT.md](AUDIT.md) for tested behavior.
