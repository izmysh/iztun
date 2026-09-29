# Publishing IZtun on GitHub

The intended project is **https://github.com/izmysh/IZtun**, developed by **IZMYSH**.
Providing a URL does not create a repository. Inspect any existing repository
before uploading; do not overwrite unrelated work.

## 1. Register or sign in

1. Open [GitHub signup](https://github.com/signup), or sign in to your existing account.
2. Choose a username, verify your email and use a unique password. If you own
   `izmysh` already, use that account rather than registering another one.
3. In **Settings → Password and authentication**, enable two-factor authentication.
   Prefer an authenticator or security key/passkey.
4. Save recovery codes privately, for example in a password manager.
5. Under **Settings → Emails**, choose whether to keep your email private. GitHub
   supplies a `noreply` address you can use for commits.

Complete account verification yourself. Never share passwords, recovery codes,
2FA codes or tokens in source files, chat messages or terminal command history.

Official references: [account registration](https://docs.github.com/en/account-and-profile/how-tos/account-management/creating-an-account-on-github),
[account setup and security](https://docs.github.com/en/get-started/onboarding/getting-started-with-your-github-account).

## 2. Publish a standalone frontend

Create **IZtun as its own repository**, not a fork of AmneziaWG-GO. Your project
contains the GUI/helper, packaging and documentation. The engine and tools retain
their upstream authors, licenses and pinned revisions.

For a first publication, use the clean complete source archive. It has ordinary
upstream source directories, no `.git` history, no `.gitmodules` and no live VPN
profiles. Do not initialize Git in your entire home folder, workspace or `/etc/amneziawg`.

## 3. Prepare a clean local checkout

Install Git and GitHub CLI with your OS package manager. Debian/Ubuntu:
`sudo apt install git gh`. Arch: `sudo pacman -S git github-cli`.
Publishing can be done on x86-64; building the supplied binary requires ARM64.

```bash
mkdir -p ~/Projects
cd ~/Projects
# Put the source archive and checksum here first.
sha256sum -c iztun-0.3.0-source.tar.gz.sha256
tar -xzf iztun-0.3.0-source.tar.gz
cd iztun-0.3.0
sha256sum -c SOURCE-MANIFEST.sha256

git init -b main
git config user.name "IZMYSH"
# Replace this with your real email or GitHub-provided noreply address.
git config user.email "YOUR_GITHUB_NOREPLY_ADDRESS"
git add .
# This is a system group definition, not a VPN config; *.conf is normally ignored.
git add -f sysusers.d/amneziawg-linux-gui.conf
git status --short
git diff --cached --stat
```

Inspect staged files. There must be no personal logs, VPN profiles, SSH keys,
tokens, addresses of customer devices or other private material. Public upstream
manuals contain example keys; those are not your credentials. Keep all licenses.

```bash
git commit -m "Initial IZtun release"
```

The original developer checkout uses pinned Git submodules. If publishing that
checkout instead, preserve its `.gitmodules` and gitlinks and verify `git submodule
status`. Do not mix the two approaches by copying parts of a `.git` directory.

## 4. Authenticate GitHub CLI

```bash
gh auth login
```

Choose **GitHub.com**, **HTTPS**, and **Login with a web browser**. Complete the
device-code/browser flow yourself. Then check:

```bash
gh auth status
```

## 5. Create and push the repository

Check whether [izmysh/IZtun](https://github.com/izmysh/IZtun) already exists.
For a new repository, from your prepared source directory:

```bash
gh repo create izmysh/IZtun --public --source=. --remote=origin --push \
  --description "Lightweight AmneziaWG-GO GUI for ARM64 Linux, by IZMYSH"
```

`--public` makes committed files public. Use `--private` for a private review if
preferred; private runner/attestation availability may differ.

If an **empty** repository already exists and you own it:

```bash
git remote add origin https://github.com/izmysh/IZtun.git
git push -u origin main
```

If it is not empty, review and merge its history first. Do not force-push over it.
You can also create an empty repository through the website's **New repository**
button. Name it **IZtun**, and do not generate a second README or license.

## 6. Check the public project

- Verify README rendering, installation commands and build instructions.
- Add topics: `amneziawg`, `vpn`, `linux`, `arm64`, `gtk`, `gui`.
- Enable private vulnerability reporting in repository security settings where available.
- Inspect **Actions**: the ARM64 workflow builds, tests and scans the engine.
- Test a fresh `git clone --recurse-submodules https://github.com/izmysh/IZtun.git`.

The archive vendors upstream source, so a repository created from it needs no
submodule download. Recursive checkout also supports the original developer repository.

## 7. Release binaries and matching sources

Build on ARM64 as described in README. Run tests, inspect the audit report and
scan the actual engine. A failed scan is not a clean scan. Choose **one** of the
following release paths so two jobs do not try to publish the same tag.

### Automatic GitHub Actions release

Confirm both `VERSION` and the GUI constant say `0.3.0`, then:

```bash
git tag -a v0.3.0 -m "IZtun 0.3.0"
git push origin v0.3.0
```

The `v*` workflow builds an ARM64 package and source archive. Watch Actions until
it succeeds. Only claim GitHub build provenance/attestation after successful execution.

### Manual upload of the Orange Pi build

If uploading the supplied files manually, disable the automatic release workflow
first to avoid a race. Open **Releases → Draft a new release**, select/create the
version tag and attach:

```text
amneziawg-linux-gui_0.3.0_arm64.deb
amneziawg-linux-gui_0.3.0_arm64.deb.sha256
iztun-0.3.0-source.tar.gz
iztun-0.3.0-source.tar.gz.sha256
```

Use title **IZtun 0.3.0**. State supported architecture, tested OS, changes,
limitations and checksum verification. Mark experimental builds **pre-release**.
These are applications, not Orange Pi firmware images.

Always ship matching upstream sources and licenses. GitHub's automatic source
ZIP is not sufficient if dependencies are submodules. Checksums detect corruption
but do not authenticate the author.

Official guide: [manage GitHub releases](https://docs.github.com/en/repositories/releasing-projects-on-github/managing-releases-in-a-repository).

## 8. Update the project

1. Make changes on a branch and review them.
2. Update `VERSION`, the GUI version and `CHANGELOG.md`.
3. Change upstream pins only after testing; keep their licenses intact.
4. Run backend/GTK tests, build a fresh `.deb`, scan it and export fresh sources.
5. Test install/rollback on ARM64 without losing profiles.
6. Commit, merge, create the new version tag and publish matching artifacts.

Do not replace already published version files with different bytes. Publish a
new version. Keep your sources and build tools for later updates.

## 9. If a secret is published accidentally

Revoke or rotate it immediately. A later deletion commit does not erase Git
history, caches or downloaded archives. Follow GitHub incident guidance and
notify affected users when necessary. Never use a live VPN profile as a public example.
