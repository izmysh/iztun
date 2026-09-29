[🇬🇧 EN](README.md) | [🇷🇺 RU](README.ru.md)

# IZtun

**A lightweight AmneziaWG-GO desktop client for ARM64 Linux.** Developed by **IZMYSH**.

Import a VPN configuration, connect and manage profiles from a native GTK window or the system tray.

[Download](https://github.com/izmysh/iztun/releases/latest) · [Manual build](BUILDING.md) · [Security](SECURITY.md)

## What you need

An ARM64 Debian/Ubuntu/Armbian system with systemd and a desktop, plus a working
AmneziaWG server and its client `.conf` file.

The ready-made package needs **glibc 2.38 or newer**. Tested on Orange Pi 5 with
ARM64 Armbian/Ubuntu. Other ARM64 boards may work but have not been validated.
The package does not support x86-64 or 32-bit ARM.

## Install

1. Download [the ARM64 .deb](https://github.com/izmysh/iztun/releases/download/v0.3.1/amneziawg-linux-gui_0.3.1_arm64.deb).
2. Open a terminal in the folder containing the downloaded file and run:

```bash
sudo apt install ./amneziawg-linux-gui_0.3.1_arm64.deb
sudo amneziawg-linux-gui-setup-user "$USER"
```

3. **Sign out of the desktop and sign back in.** Open **IZtun** from the application menu.

The package installs the GUI, VPN engine and command-line tools together.
The internal package name remains `amneziawg-linux-gui` for upgrade compatibility.
If `apt` cannot find a dependency, run `sudo apt update` and try again.

## Use

- **+** imports a `.conf` profile.
- **Connect / Disconnect** starts or stops the VPN.
- **Auto-connect** connects at system boot.
- **⋮** opens Rename, Edit configuration, Repair and diagnostic export.
- The tray lets you control profiles without keeping the window open.

AWG 2, 3 and 3.1 parameters are supported. A new full-tunnel connection replaces
the previous one; if it fails, IZtun attempts to restore the previous VPN.
Edit a profile while disconnected. Closing the window hides it in the tray;
quitting the GUI does not disconnect the VPN.

A recent handshake proves peer authentication, not Internet or DNS availability.
**There is no kill switch.** Traffic may use the ordinary network after failure
or disconnection.

## Install from source

Download [the complete source archive](https://github.com/izmysh/iztun/releases/download/v0.3.1/iztun-0.3.1-source.tar.gz)
and unpack it with your file manager. Open a terminal inside the unpacked folder
and run this **as your regular user**:

```bash
bash scripts/install-from-source.sh
```

The installer downloads dependencies, compiles AmneziaWG-GO and its tools,
builds IZtun's package and installs it. It asks for your administrator password
when needed. Internet access is required. Sign out and back in after installation.

For separate engine compilation, checksums, tests and custom builds, see
[the manual build guide](BUILDING.md). Keep the source folder and compiler for future updates.

## Troubleshooting

- **Access denied:** sign out and back in after user setup.
- **No connection:** check your server/config, then try **Repair connection**.
- **No tray:** enable StatusNotifier/AppIndicator support in your panel.
- **Helper unavailable:** see [the service checks](BUILDING.md#service-checks).

The GUI runs without `sudo`. The privileged helper manages routes and DNS.
Only add trusted users to the `amneziawg` group; its members can read profile
keys through the editor. Never publish VPN configs or editor screenshots.

## Updates and removal

Install a newer `.deb` in the same way. To remove the application, disconnect first:

```bash
sudo apt remove amneziawg-linux-gui
```

Profiles in `/etc/amneziawg`, deleted-profile backups and your source folder are retained.

## Project

IZtun is an independent frontend, not an official Amnezia application.
IZtun and AmneziaWG-GO use MIT licenses; the bundled tools use GPL-2.0.

[Contributing](CONTRIBUTING.md) · [Audit and limits](AUDIT.md) ·
[Licenses](THIRD_PARTY_NOTICES.md) · [GitHub publishing](PUBLISHING.md)
