PREFIX ?= /usr
DESTDIR ?=
PYTHON ?= python3
export GOTOOLCHAIN := go1.26.8

GO_SOURCE := upstream/amneziawg-go
TOOLS_SOURCE := upstream/amneziawg-tools
ENGINE_BUILD := build/engine
GO_BUILD_SOURCE := build/amneziawg-go-source
TOOLS_BUILD_SOURCE := build/amneziawg-tools-source
GO_TAG := v3.1.20260828

.PHONY: all upstream engine test audit install deb source-bundle clean

all: test engine

upstream:
	git submodule update --init --recursive

engine:
	test -f "$(GO_SOURCE)/go.mod"
	test -f "$(TOOLS_SOURCE)/src/Makefile"
	rm -rf "$(GO_BUILD_SOURCE)" "$(TOOLS_BUILD_SOURCE)" "$(ENGINE_BUILD)"
	mkdir -p "$(GO_BUILD_SOURCE)" "$(TOOLS_BUILD_SOURCE)" "$(ENGINE_BUILD)"
	cp -a "$(GO_SOURCE)/." "$(GO_BUILD_SOURCE)/"
	rm -rf "$(GO_BUILD_SOURCE)/.git"
	printf 'package main\n\nconst Version = "%s"\n' "$(GO_TAG)" >"$(GO_BUILD_SOURCE)/version.go"
	cd "$(GO_BUILD_SOURCE)" && CGO_ENABLED=0 go build -mod=readonly -trimpath -buildvcs=false -o "$(abspath $(ENGINE_BUILD))/amneziawg-go"
	cp -a "$(TOOLS_SOURCE)/." "$(TOOLS_BUILD_SOURCE)/"
	$(MAKE) -C "$(TOOLS_BUILD_SOURCE)/src" clean
	CFLAGS="-O2 -D_FORTIFY_SOURCE=3 -fstack-protector-strong -fPIE" LDFLAGS="-pie -Wl,-z,relro,-z,now" $(MAKE) -C "$(TOOLS_BUILD_SOURCE)/src" WIREGUARD_TOOLS_VERSION=3.1.20260812
	cp "$(TOOLS_BUILD_SOURCE)/src/wg" "$(ENGINE_BUILD)/awg"
	cp "$(TOOLS_SOURCE)/src/wg-quick/linux.bash" "$(ENGINE_BUILD)/awg-quick"
	chmod 0755 "$(ENGINE_BUILD)/amneziawg-go" "$(ENGINE_BUILD)/awg" "$(ENGINE_BUILD)/awg-quick"

test:
	$(PYTHON) -m py_compile src/amneziawg-linux-gui src/amneziawg-linux-gui-helper
	$(PYTHON) -m unittest discover -s tests -v

audit:
	cd "$(GO_BUILD_SOURCE)" && go run golang.org/x/vuln/cmd/govulncheck@v1.8.0 -mode=binary "$(abspath $(ENGINE_BUILD))/amneziawg-go"

install:
	test -x "$(ENGINE_BUILD)/amneziawg-go"
	test -x "$(ENGINE_BUILD)/awg"
	install -Dm0755 src/amneziawg-linux-gui "$(DESTDIR)$(PREFIX)/bin/amneziawg-linux-gui"
	ln -sfn amneziawg-linux-gui "$(DESTDIR)$(PREFIX)/bin/iztun"
	install -Dm0755 src/amneziawg-linux-gui-helper "$(DESTDIR)$(PREFIX)/libexec/amneziawg-linux-gui-helper"
	install -Dm0755 src/amneziawg-linux-gui-setup-user "$(DESTDIR)$(PREFIX)/sbin/amneziawg-linux-gui-setup-user"
	install -Dm0755 "$(ENGINE_BUILD)/amneziawg-go" "$(DESTDIR)$(PREFIX)/bin/amneziawg-go"
	install -Dm0755 "$(ENGINE_BUILD)/awg" "$(DESTDIR)$(PREFIX)/bin/awg"
	install -Dm0755 "$(ENGINE_BUILD)/awg-quick" "$(DESTDIR)$(PREFIX)/bin/awg-quick"
	install -Dm0644 systemd/amneziawg-linux-gui.socket "$(DESTDIR)$(PREFIX)/lib/systemd/system/amneziawg-linux-gui.socket"
	install -Dm0644 systemd/amneziawg-linux-gui@.service "$(DESTDIR)$(PREFIX)/lib/systemd/system/amneziawg-linux-gui@.service"
	install -Dm0644 systemd/amneziawg@.service "$(DESTDIR)$(PREFIX)/lib/systemd/system/amneziawg@.service"
	install -Dm0644 systemd/amneziawg-recover.service "$(DESTDIR)$(PREFIX)/lib/systemd/system/amneziawg-recover.service"
	install -Dm0755 data/90-amneziawg-linux-gui "$(DESTDIR)$(PREFIX)/lib/NetworkManager/dispatcher.d/90-amneziawg-linux-gui"
	install -Dm0755 data/90-amneziawg-networkd "$(DESTDIR)$(PREFIX)/lib/networkd-dispatcher/routable.d/90-amneziawg-linux-gui"
	install -Dm0755 data/amneziawg-linux-gui-sleep "$(DESTDIR)$(PREFIX)/lib/systemd/system-sleep/amneziawg-linux-gui"
	install -Dm0644 sysusers.d/amneziawg-linux-gui.conf "$(DESTDIR)$(PREFIX)/lib/sysusers.d/amneziawg-linux-gui.conf"
	install -Dm0644 data/io.github.amneziawg_linux_gui.Client.desktop "$(DESTDIR)$(PREFIX)/share/applications/io.github.amneziawg_linux_gui.Client.desktop"
	install -Dm0644 README.md "$(DESTDIR)$(PREFIX)/share/doc/amneziawg-linux-gui/README.md"
	install -Dm0644 README.ru.md "$(DESTDIR)$(PREFIX)/share/doc/amneziawg-linux-gui/README.ru.md"
	install -Dm0644 BUILDING.md "$(DESTDIR)$(PREFIX)/share/doc/amneziawg-linux-gui/BUILDING.md"
	install -Dm0644 BUILDING.ru.md "$(DESTDIR)$(PREFIX)/share/doc/amneziawg-linux-gui/BUILDING.ru.md"
	install -Dm0644 CHANGELOG.md "$(DESTDIR)$(PREFIX)/share/doc/amneziawg-linux-gui/CHANGELOG.md"
	install -Dm0644 LICENSE "$(DESTDIR)$(PREFIX)/share/doc/amneziawg-linux-gui/LICENSE"
	install -Dm0644 THIRD_PARTY_NOTICES.md "$(DESTDIR)$(PREFIX)/share/doc/amneziawg-linux-gui/THIRD_PARTY_NOTICES.md"
	install -Dm0644 upstream/amneziawg-go/LICENSE "$(DESTDIR)$(PREFIX)/share/doc/amneziawg-linux-gui/amneziawg-go.LICENSE"
	install -Dm0644 upstream/amneziawg-tools/COPYING "$(DESTDIR)$(PREFIX)/share/doc/amneziawg-linux-gui/amneziawg-tools.COPYING"

deb:
	packaging/build-deb.sh

source-bundle:
	packaging/source-bundle.sh

clean:
	rm -rf build dist
	$(MAKE) -C "$(TOOLS_SOURCE)/src" clean 2>/dev/null || true
