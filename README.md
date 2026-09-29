[🇬🇧 EN](README.md) | [🇷🇺 RU](README.ru.md)

# IZtun

**A lightweight desktop GUI for AmneziaWG-GO on ARM64 Linux.** Developed by **IZMYSH**.

Import a `.conf` file, connect, and manage your VPN from a native GTK window or
the system tray. No Electron or browser runtime.

[Project](https://github.com/izmysh/IZtun) · [Releases](https://github.com/izmysh/IZtun/releases) ·
[Security](SECURITY.md) · [Audit](AUDIT.md) · [Publishing guide](PUBLISHING.md)

> IZtun is an independent frontend, not an official Amnezia application or a new
> VPN protocol. You need your own working VPN server and client configuration.

## Features

- Import AmneziaWG `.conf` profiles with AWG 2, 3 and 3.1 parameters.
- Connect, disconnect, repair, and optionally connect at boot.
- Switch full tunnels; attempt to restore the previous connection if the new one fails.
- Keep compatible split tunnels for separate private networks.
- Rename profiles and edit configs with validation and a protected previous version.
- Display handshake-based status, connection progress, speed and session traffic.
- Recover after supported network-change and resume events.
- Export diagnostics without configuration contents or private keys.

## Requirements

The `.deb` is for **ARM64 / aarch64**, not x86-64 or 32-bit ARM. It targets
Debian/Ubuntu/Armbian with systemd, GTK 3 and `/dev/net/tun`. The release is tested
on an Orange Pi 5 running ARM64 Armbian/Ubuntu. There is no Orange Pi-specific
CPU/GPU code, but other boards have not been validated.

The current C tool requires **glibc 2.38 or newer**; the package declares the
minimum version required by its actual binary. Ubuntu 24.04+ and Debian 13 are
candidate targets, not a claim of testing every setup. Build on the target OS
for older distributions. This `.deb` is not an Android, Arch, Alpine, Windows
or macOS package.

```bash
uname -m                    # Expected: aarch64
dpkg --print-architecture   # Expected: arm64
getconf GNU_LIBC_VERSION
test -c /dev/net/tun && echo 'TUN available'
```

## Install the Debian package

Download the `.deb` and its `.sha256` file from a release you trust. In their directory:

```bash
# Check download integrity; a checksum is not an author signature.
sha256sum -c amneziawg-linux-gui_0.3.0_arm64.deb.sha256
sudo apt update
sudo apt install ./amneziawg-linux-gui_0.3.0_arm64.deb
sudo amneziawg-linux-gui-setup-user "$USER"
```

**Sign out of the desktop and sign in again** to activate group membership.
Open **IZtun** from the application menu, or run `iztun`.

Do not run the GUI with `sudo`. The restricted helper and tunnel services use
administrative privileges. Members of `amneziawg` can change routes/DNS and read
VPN keys through the editor: only add trusted users.

The package bundles `amneziawg-go`, `awg` and `awg-quick`. It conflicts with
separately installed packages owning those tools; review any removal proposed by
`apt` before accepting it. Internal package/service IDs retain the earlier
`amneziawg-linux-gui` name for upgrade compatibility. The visible application and
launcher command are **IZtun** and `iztun`.

## Everyday use

1. Press **+** and choose a `.conf` file exported for your VPN server.
2. Give its interface a short ID: up to 15 ASCII letters/digits and supported separators.
3. Press **Connect**. A fresh handshake proves peer authentication, not Internet or DNS reachability.
4. Use **⋮ → Rename…** for a friendly display name, including Unicode.
5. Use **⋮ → Edit configuration…** while disconnected. Changes apply on the next connection.

**Auto-connect** means connect at system boot, not launch the GUI. Enable it for
your preferred full tunnel rather than several competing profiles. Closing the
window hides it in the tray. Quitting the GUI does not disconnect a system-managed
VPN; use **Disconnect** for that.

Bottom-right counters show combined traffic for active tunnels, updated every
five seconds while visible. They reset when tunnels are recreated; they are not
permanent monthly usage statistics.

**No kill switch is provided.** Switching, failure or disconnection may expose
ordinary network connectivity. Split-tunnel routes and DNS must be compatible.

## Build from source on ARM64

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
git clone --recurse-submodules https://github.com/izmysh/IZtun.git
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

## Troubleshooting

**Access denied:** sign out/in after setup. `id -nG` must include `amneziawg`.
Otherwise run `sudo amneziawg-linux-gui-setup-user "$USER"`, then sign in again.

**Helper unavailable:**

```bash
systemctl status amneziawg-linux-gui.socket
sudo systemctl enable --now amneziawg-linux-gui.socket
```

**No handshake:** check server availability, endpoint, keys and protocol parameters.
Try **Repair connection** and export a redacted report from **⋮**. Never publish
raw configs or screenshots of the editor: they contain private keys.

**Invalid config:** shell hooks (`PreUp`, `PostUp`, `PreDown`, `PostDown`),
`SaveConfig`, custom routing tables and firewall marks are intentionally rejected.
Use conventional spellings such as `AllowedIPs`, not `Allowed IPs`. Disconnect
before editing. A malformed file no longer hides other profiles.

**DNS problems:** configs using `DNS` require working `resolvconf` integration.
Fix the distribution's resolver setup rather than overwriting `/etc/resolv.conf`.

**No tray:** enable StatusNotifier/AppIndicator support in your desktop/panel.
Running `iztun` reopens the window.

**Recovery:** hooks are supplied for NetworkManager and networkd-dispatcher.
On systemd-networkd systems install/enable `networkd-dispatcher`. Actual resume
and cable-reconnection behavior depends on the OS; see [AUDIT.md](AUDIT.md).

## Updates, files and uninstalling

Install a new `.deb` with `sudo apt install ./PACKAGE.deb`, then reopen IZtun.
Profiles remain in `/etc/amneziawg` with root-only access. Deleted profiles go
to `/etc/amneziawg/.trash`; edits keep `PROFILE.conf.previous`. These contain
private keys and must never be committed to Git.

Disconnect first, then uninstall:

```bash
sudo apt remove amneziawg-linux-gui
```

Profiles are intentionally kept, even on purge. Remove them separately only when
you no longer need their keys. Removing IZtun does not remove your source tree or compiler.

## Contributing, publishing and licensing

See [CONTRIBUTING.md](CONTRIBUTING.md), [SECURITY.md](SECURITY.md) and the step-by-step
[GitHub publishing guide](PUBLISHING.md). Never commit account or VPN credentials.

IZtun is MIT-licensed ([LICENSE](LICENSE)). Bundled AmneziaWG-GO is MIT-licensed;
AmneziaWG tools are GPL-2.0. Keep upstream notices and matching sources with your
releases. Details: [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
