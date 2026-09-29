[🇬🇧 EN](BUILDING.md) | [🇷🇺 RU](BUILDING.ru.md)

[Вернуться к README](README.ru.md)

# Ручная сборка на ARM64

Собирайте от обычного пользователя. `sudo` нужен для установки системных
зависимостей и пакета. Сохраните исходники и компилятор для будущих обновлений.

### 1. Установите зависимости

```bash
sudo apt update
sudo apt install build-essential binutils pkg-config dpkg-dev git golang-go \
  python3 python3-gi gir1.2-gtk-3.0 gir1.2-ayatanaappindicator3-0.1 \
  iproute2 iptables resolvconf systemd
```

В подходящем дистрибутиве можно использовать `openresolv` вместо `resolvconf`.
Перед заменой проверьте изменения в интеграции DNS, предлагаемые пакетным менеджером.

Сборка использует **Go 1.26.8**. Достаточно свежая версия Go из дистрибутива
загружает выбранную цепочку инструментов автоматически. Если это не поддерживается,
установите Go по [официальной инструкции](https://go.dev/doc/install).

Архив содержит исходники движка и инструментов, но не системные пакеты,
компилятор Go или кэш его модулей. Для первой сборки нужен интернет.
Версии и контрольные суммы Go-зависимостей зафиксированы в `go.mod` и `go.sum`.

### 2. Получите исходники

Скачайте полный архив исходников и контрольную сумму из нужного релиза:

```bash
sha256sum -c iztun-0.3.1-source.tar.gz.sha256
tar -xzf iztun-0.3.1-source.tar.gz
cd iztun-0.3.1
sha256sum -c SOURCE-MANIFEST.sha256
```

Для этого архива не нужны инициализация Git и скачивание submodule.
Альтернативный способ - клонировать репозиторий:

```bash
git clone --recurse-submodules https://github.com/izmysh/iztun.git IZtun
cd IZtun
```

Автоматически созданный GitHub ZIP может не содержать submodule.
Полный архив из релиза включает обе upstream-зависимости.

### 3. Скомпилируйте AmneziaWG-GO и инструменты командной строки

Основная команда собирает обе зафиксированные upstream-зависимости в `build/`:

```bash
make engine
file build/engine/amneziawg-go build/engine/awg
build/engine/amneziawg-go --version
build/engine/awg --version
```

Если хотите выполнить шаги вручную, начните с Go-движка из корня проекта.
Эти команды только создают бинарник - не устанавливают его и не подключают VPN:

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

`CGO_ENABLED=0` убирает зависимость Go-движка от C runtime.
Отдельная команда `awg` написана на C и по-прежнему требует libc.
Чтобы собрать ее и подготовить `awg-quick`, выполните:

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

`make engine` выполняет эти шаги автоматически и очищает старые объектные файлы.
Точные теги и коммиты указаны в [UPSTREAM_VERSIONS](UPSTREAM_VERSIONS).
IZtun использует upstream-реализацию протокола и криптографии.

### 4. Проверьте IZtun и соберите пакет

GUI и помощник написаны на Python, поэтому отдельная компиляция в ARM-код
не нужна. Следующие команды проверяют синтаксис, запускают тесты и собирают
пакет приложения вместе с движками:

```bash
make test
make deb
make source-bundle
```

`make deb` повторно запускает тесты и собирает движки, чтобы не упаковать старые бинарники.
Готовые файлы:

```text
dist/amneziawg-linux-gui_0.3.1_arm64.deb
dist/amneziawg-linux-gui_0.3.1_arm64.deb.sha256
dist/iztun-0.3.1-source.tar.gz
dist/iztun-0.3.1-source.tar.gz.sha256
```

Установите полученный пакет:

```bash
sudo apt install ./dist/amneziawg-linux-gui_0.3.1_arm64.deb
sudo amneziawg-linux-gui-setup-user "$USER"
# Выйдите из сеанса и войдите снова, затем запустите:
iztun
```

`bash scripts/install-from-source.sh` объединяет эти действия в установщик.
Он устанавливает системные пакеты; перед запуском можно прочитать его исходник.

### 5. Дополнительные проверки

```bash
# Проверка поставляемого движка по базе Go-уязвимостей. Нужен интернет.
make audit
# GUI-тесты используют искусственные профили без настоящего подключения к VPN.
sudo apt install xvfb xauth
xvfb-run -a python3 scripts/verify-gui.py --source src/amneziawg-linux-gui
```

В `verify-installed.py` и `verify-profile-actions.py` есть дополнительные
интеграционные проверки сети. Перед запуском прочитайте `--help`: live-проверки
подключают и отключают туннели. Не запускайте их во время важной удаленной работы.

## Проверка службы

```bash
systemctl status amneziawg-linux-gui.socket
sudo systemctl enable --now amneziawg-linux-gui.socket
```

При использовании systemd-networkd для восстановления после смены сети
нужно также установить и включить `networkd-dispatcher`.
Проверенные сценарии перечислены в [AUDIT.md](AUDIT.md).
