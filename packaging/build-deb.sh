#!/bin/sh
set -eu

project_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
version=$(cat "$project_dir/VERSION")
architecture=arm64
package_name=iztun

if [ "$(uname -m)" != "aarch64" ]; then
    echo "build-deb.sh must run on an ARM64 Linux host or ARM64 GitHub runner." >&2
    exit 1
fi

make -C "$project_dir" test
make -C "$project_dir" engine

stage=$(mktemp -d)
trap 'rm -rf "$stage"' EXIT INT TERM
chmod 0755 "$stage"

make -C "$project_dir" install DESTDIR="$stage"
mkdir -p "$stage/DEBIAN" "$project_dir/dist"

installed_size=$(du -sk "$stage/usr" | awk '{print $1}')
libc_min=$(LC_ALL=C readelf --version-info "$stage/usr/bin/awg" | sed -n 's/.*Name: GLIBC_\([0-9.]*\).*/\1/p' | sort -V | tail -1)
test -n "$libc_min"
cat >"$stage/DEBIAN/control" <<EOF
Package: $package_name
Version: $version
Section: net
Priority: optional
Architecture: $architecture
Installed-Size: $installed_size
Maintainer: IZtun contributors
Depends: bash, libc6 (>= $libc_min), iproute2, iptables, python3, python3-gi, gir1.2-gtk-3.0, gir1.2-ayatanaappindicator3-0.1, systemd, pkexec, policykit-1-gnome, passwd, resolvconf | openresolv
Conflicts: amneziawg-linux-gui, amneziawg-tools, amneziawg-go
Replaces: amneziawg-linux-gui
Recommends: resolvconf | openresolv
Description: IZtun - independent lightweight GTK client for AmneziaWG
 A small desktop client for importing and controlling AmneziaWG profiles on
 ARM64 Debian, Ubuntu and Armbian systems. It bundles pinned builds of
 amneziawg-go and amneziawg-tools.
EOF

cat >"$stage/DEBIAN/postinst" <<'EOF'
#!/bin/sh
set -e
systemd-sysusers /usr/lib/sysusers.d/amneziawg-linux-gui.conf
if [ -L /etc/amneziawg ]; then
    echo 'Refusing symlink /etc/amneziawg' >&2
    exit 1
fi
install -d -o root -g root -m 0700 /etc/amneziawg
if [ -d /run/systemd/system ]; then
    systemctl daemon-reload
    systemctl enable --now amneziawg-linux-gui.socket
fi
echo "Open IZtun from your application menu. First-launch access setup is automatic."
EOF

cat >"$stage/DEBIAN/prerm" <<'EOF'
#!/bin/sh
set -e
if [ "$1" = remove ]; then
    systemctl stop 'amneziawg@*.service' >/dev/null 2>&1 || true
    systemctl disable --now amneziawg-linux-gui.socket >/dev/null 2>&1 || true
fi
EOF

cat >"$stage/DEBIAN/postrm" <<'EOF'
#!/bin/sh
set -e
systemctl daemon-reload >/dev/null 2>&1 || true
if [ "$1" = purge ]; then
    echo "VPN profiles were intentionally kept in /etc/amneziawg. Remove them manually if no longer needed."
fi
EOF

chmod 0755 "$stage/DEBIAN/postinst" "$stage/DEBIAN/prerm" "$stage/DEBIAN/postrm"
output="$project_dir/dist/${package_name}_${version}_${architecture}.deb"
dpkg-deb --root-owner-group --build "$stage" "$output"
(cd "$(dirname "$output")" && sha256sum "$(basename "$output")" >"$(basename "$output").sha256")
echo "$output"
