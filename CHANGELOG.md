# Changelog

## 0.3.2

- bundle administrator-approved first-launch access setup; no manual group command or logout;
- keep the GUI unprivileged and retain the private command socket;
- explain the bundled VPN engine, upstream links and independent frontend status in both READMEs;
- use the declared binutils dependency for build-guide architecture checks.

## 0.3.1

- simplify both READMEs: two commands for the Debian package and one source installer command;
- move separate ARM64 engine compilation and contributor checks to dedicated build guides;
- use plain hyphens and normalize Russian documentation typography;
- include both build guides in packages and source archives.

## 0.3.0

- provide English and Russian READMEs with language links;
- add an About button, IZMYSH credit and the project link; remove the header subtitle;
- reject disguised directives that could bypass routing and full-tunnel restrictions;
- bound privileged file/socket reads and lock waits; coordinate safe stop timeouts;
- keep other profiles usable when one configuration is invalid;
- batch service status reads and prevent overlapping workers and stale UI updates;
- use nonblocking dialogs, bounded imports and private diagnostic files;
- open file dialogs in the user's home, never an inherited inaccessible working directory;
- include upstream license texts and harden the ARM64 C tool build;
- build allowlisted source archives with a file manifest and secret checks;
- document installation, ARM64 source builds and GitHub publishing in English.

## 0.2.2

- rename the desktop application to IZtun; retain service/package IDs for upgrades;
- replace static introductory/footer text with bottom-right connection status and traffic;
- keep read-only status updates running during connection operations;
- add Unicode display names and a validated editor for disconnected profiles;
- atomically save edits with stale-edit detection and one protected backup;
- switch full tunnels automatically, restoring the previous tunnel on failure;
- remove the redundant idle detail line;

## 0.2.1
- align profile controls in shared columns with a single autostart heading;
- eliminate privileged arbitrary-path imports; bound and validate socket input;
- protect boot-time activation with the same conflict lock as GUI actions;
- authenticate full tunnels before reporting success; roll back failed handshakes;
- preserve manual Disconnect across network changes until reconnect or reboot;
- capture engine output without disclosing config values in error messages;
- fix the helper's read-only runtime directory and peer endpoint parsing;
- serialize UI actions, restore buttons after errors and avoid periodic error dialogs;
- poll hidden windows every 15 seconds and remove redundant service/config reads;
- add security and rollback regression coverage.

## 0.2.0

- report connection health from the service, interface and latest handshake;
- recover enabled or previously active tunnels after resume and network changes;
- add a one-click connection repair action;
- roll back profile-owned interface, DNS, firewall and routing state after failures;
- export diagnostics without keys, profile contents or endpoint addresses;
- control individual profiles from the tray menu;
- prevent two full-tunnel profiles from running at the same time;
- simplify each profile row around status, automatic recovery and one primary action.

## 0.1.0

- initial ARM64 GTK client and Debian package.
