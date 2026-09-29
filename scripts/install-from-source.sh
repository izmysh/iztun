#!/bin/sh
set -eu

project_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)

if [ "$(uname -m)" != "aarch64" ]; then
    echo "This installer currently builds native ARM64 packages only." >&2
    exit 1
fi

sudo apt-get update
sudo apt-get install -y \
    build-essential git golang-go dpkg-dev \
    python3 python3-gi gir1.2-gtk-3.0 gir1.2-ayatanaappindicator3-0.1 \
    bash iproute2 iptables resolvconf systemd

if [ ! -f "$project_dir/upstream/amneziawg-go/go.mod" ]; then
    git -C "$project_dir" submodule update --init --recursive
fi
make -C "$project_dir" deb
sudo apt-get install -y "$project_dir/dist/iztun_$(cat "$project_dir/VERSION")_arm64.deb"

echo "Installation completed. Open IZtun; it will request administrator approval if access needs setup."
