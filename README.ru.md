[🇬🇧 EN](README.md) | [🇷🇺 RU](README.ru.md)

# IZtun

**Лёгкий графический клиент для AmneziaWG-GO на ARM64 Linux.** Разработано **IZMYSH**.

Загрузите файл `.conf`, подключитесь к VPN и управляйте профилями через нативное
окно GTK или системный трей. Electron и браузер для работы приложения не нужны.

[Проект](https://github.com/izmysh/IZtun) · [Релизы](https://github.com/izmysh/IZtun/releases) ·
[Безопасность](SECURITY.md) · [Отчёт проверки](AUDIT.md) · [Публикация на GitHub](PUBLISHING.md)

> IZtun — независимая GUI-надстройка. Это не официальное приложение Amnezia
> и не отдельный VPN-протокол. Для подключения нужны работающий VPN-сервер
> и подходящий клиентский конфиг.

## Возможности

- Импорт `.conf` с параметрами AmneziaWG 2, 3 и 3.1.
- Подключение, отключение, восстановление соединения и автоподключение при загрузке.
- Переключение между полными туннелями с попыткой вернуть прежнее соединение,
  если новое подключение не удалось.
- Одновременная работа совместимых split-tunnel профилей для отдельных сетей.
- Переименование профилей и редактирование конфигов с проверкой и сохранением
  защищённой предыдущей версии.
- Состояние подключения по handshake, прогресс, скорость и трафик текущего сеанса.
- Восстановление после поддерживаемых событий смены сети и выхода из сна.
- Диагностический отчёт без содержимого конфигов и приватных ключей.

## Системные требования

Готовый `.deb` предназначен для **ARM64 / aarch64**. Для x86-64 и 32-битного ARM
он не подходит. Требуются Debian/Ubuntu/Armbian, systemd, GTK 3 и `/dev/net/tun`.
Релиз проверен на Orange Pi 5 с ARM64 Armbian/Ubuntu. Привязки к процессору или
GPU Orange Pi в коде нет; другие платы пока не проверялись.

Для поставляемого инструмента `awg` нужна **glibc 2.38 или новее**. Пакет указывает
минимальную версию, требуемую собранным бинарником. Ubuntu 24.04+ и Debian 13 —
возможные целевые системы, а не перечень проверенных конфигураций. Для более
старого дистрибутива собирайте приложение на целевой системе.
Этот `.deb` не предназначен для Android, Arch, Alpine, Windows или macOS.

```bash
uname -m                    # Ожидается: aarch64
dpkg --print-architecture   # Ожидается: arm64
getconf GNU_LIBC_VERSION
test -c /dev/net/tun && echo 'TUN available'
```

## Установка готового пакета

Скачайте `.deb` и соответствующий `.sha256` из релиза. В папке с файлами выполните:

```bash
# Проверка целостности загрузки. Контрольная сумма не заменяет подпись автора.
sha256sum -c amneziawg-linux-gui_0.3.0_arm64.deb.sha256
sudo apt update
sudo apt install ./amneziawg-linux-gui_0.3.0_arm64.deb
sudo amneziawg-linux-gui-setup-user "$USER"
```

**Выйдите из сеанса рабочего стола и войдите снова**, чтобы применилось членство
в группе. Откройте **IZtun** из меню приложений или командой `iztun`.

GUI запускается от обычного пользователя. Службы туннеля и ограниченный помощник
работают с административными правами. Участники группы `amneziawg` могут менять
маршруты/DNS и читать ключи через редактор профилей. Добавляйте в неё доверенных пользователей.

Пакет содержит `amneziawg-go`, `awg` и `awg-quick`. Он конфликтует с отдельными
пакетами, устанавливающими те же инструменты; проверяйте предлагаемые `apt`
изменения перед подтверждением. Внутреннее имя пакета и служб
`amneziawg-linux-gui` сохранено для совместимости обновлений.
Название приложения — **IZtun**, команда запуска — `iztun`.

## Использование

1. Нажмите **+** и выберите `.conf`, экспортированный для вашего VPN-сервера.
2. Укажите короткий ID интерфейса: до 15 ASCII-букв, цифр и поддерживаемых разделителей.
3. Нажмите **Connect**. Свежий handshake подтверждает аутентификацию с сервером,
   но сам по себе не гарантирует доступность интернета или DNS.
4. Для удобного имени, в том числе на русском, используйте **⋮ → Rename…**.
5. Чтобы изменить конфиг, сначала отключите профиль и выберите
   **⋮ → Edit configuration…**. Изменения применятся при следующем подключении.

**Auto-connect** включает подключение при загрузке системы, а не запуск окна GUI.
Выбирайте один основной full-tunnel профиль для автоматического подключения.
Закрытие окна прячет приложение в трей. Выход из GUI не останавливает VPN,
которым управляет systemd; для отключения используйте **Disconnect**.

Счётчики справа внизу показывают общий трафик активных туннелей и обновляются
каждые пять секунд, пока окно видно. При пересоздании туннеля они сбрасываются.
Это статистика текущего сеанса, а не постоянный месячный учёт.

**Kill switch не реализован.** Во время переключения, ошибки или отключения
может работать обычное интернет-соединение. Маршруты и DNS одновременно
работающих split-tunnel профилей должны быть совместимы.

## Сборка из исходников на ARM64

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
sha256sum -c iztun-0.3.0-source.tar.gz.sha256
tar -xzf iztun-0.3.0-source.tar.gz
cd iztun-0.3.0
sha256sum -c SOURCE-MANIFEST.sha256
```

Для этого архива не нужны инициализация Git и скачивание submodule.
Альтернативный способ — клонировать репозиторий:

```bash
git clone --recurse-submodules https://github.com/izmysh/IZtun.git
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
Эти команды только создают бинарник — не устанавливают его и не подключают VPN:

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
Чтобы собрать её и подготовить `awg-quick`, выполните:

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
dist/amneziawg-linux-gui_0.3.0_arm64.deb
dist/amneziawg-linux-gui_0.3.0_arm64.deb.sha256
dist/iztun-0.3.0-source.tar.gz
dist/iztun-0.3.0-source.tar.gz.sha256
```

Установите полученный пакет:

```bash
sudo apt install ./dist/amneziawg-linux-gui_0.3.0_arm64.deb
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
подключают и отключают туннели. Не запускайте их во время важной удалённой работы.

## Решение проблем

**Access denied:** выйдите из сеанса и войдите снова после настройки пользователя.
Команда `id -nG` должна показывать группу `amneziawg`. Если её нет:

```bash
sudo amneziawg-linux-gui-setup-user "$USER"
```

Затем повторно войдите в сеанс.

**Помощник недоступен:**

```bash
systemctl status amneziawg-linux-gui.socket
sudo systemctl enable --now amneziawg-linux-gui.socket
```

**Нет handshake:** проверьте сервер, endpoint, ключи и параметры протокола.
Попробуйте **Repair connection** и сохраните диагностический отчёт через **⋮**.
Конфиги и снимки редактора содержат приватные ключи; не публикуйте их.

**Invalid config:** shell hooks (`PreUp`, `PostUp`, `PreDown`, `PostDown`),
`SaveConfig`, пользовательские таблицы маршрутизации и firewall marks запрещены.
Используйте обычные имена параметров: `AllowedIPs`, а не `Allowed IPs`.
Для редактирования сначала отключите профиль. Один повреждённый конфиг
не скрывает остальные профили.

**Проблемы с DNS:** параметр `DNS` требует работающей интеграции `resolvconf`.
Проверьте настройки DNS дистрибутива, а не перезаписывайте `/etc/resolv.conf`.

**Нет трея:** включите поддержку StatusNotifier/AppIndicator в рабочем столе
или панели. Команда `iztun` снова открывает окно.

**Восстановление соединения:** предусмотрены hooks для NetworkManager
и networkd-dispatcher. Если используется systemd-networkd, установите и включите
`networkd-dispatcher`. Поведение после сна и переподключения кабеля зависит
от ОС; проверенные сценарии перечислены в [AUDIT.md](AUDIT.md).

## Обновления, файлы и удаление

Для обновления установите новый `.deb` командой `sudo apt install ./PACKAGE.deb`
и снова откройте IZtun. Профили хранятся в `/etc/amneziawg` с доступом только root.
Удалённые профили перемещаются в `/etc/amneziawg/.trash`, а перед редактированием
сохраняется `PROFILE.conf.previous`. Эти файлы содержат приватные ключи.

Сначала отключите VPN, затем удалите приложение:

```bash
sudo apt remove amneziawg-linux-gui
```

Профили намеренно сохраняются даже после purge. Удаляйте их отдельно, когда
они больше не нужны. Исходники и компилятор при удалении IZtun сохраняются.

## Участие в разработке и лицензии

См. [CONTRIBUTING.md](CONTRIBUTING.md), [SECURITY.md](SECURITY.md) и
[инструкцию публикации на GitHub](PUBLISHING.md). Остальная документация
проекта и интерфейс приложения — на английском.

IZtun распространяется под MIT ([LICENSE](LICENSE)). AmneziaWG-GO — под MIT,
а AmneziaWG tools — под GPL-2.0. Сохраняйте upstream-уведомления о лицензиях
и поставляйте соответствующие исходники вместе с релизами.
Подробнее: [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
