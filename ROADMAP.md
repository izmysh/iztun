# Product roadmap

The project should remain a small AmneziaWG profile client, not grow into a
second all-purpose VPN platform. New features must improve connection
reliability, recovery, diagnostics or daily profile handling.

## 0.2: reliability essentials (completed)

### Real connection health

Do not equate an existing network interface with a working VPN. Show:

- interface state;
- latest handshake age;
- whether traffic is moving;
- a clear `Connected`, `Waiting for handshake` or `Connection problem` state.

### Transactional connect and rollback

If tunnel activation fails after changing DNS or routes, automatically restore
the previous network state. Never leave the machine offline after a failed
connection attempt where cleanup succeeds. Report failures that require manual repair.

### Resume and network-change recovery

Detect suspend/resume, Wi-Fi roaming and Ethernet reconnection. Re-establish an
enabled tunnel after the network is usable, with bounded retries and backoff.

### Repair connection

Provide one explicit repair action that:

1. stops the affected tunnel;
2. removes only routes and DNS state owned by that profile;
3. starts it again;
4. reports the exact failing stage if recovery is unsuccessful.

### Safe diagnostics export

Create a small text report containing versions, service state, routes, DNS,
handshake age and redacted errors. Never include private keys, preshared keys
or complete profile files.

### Full-tunnel conflict prevention

Detect profiles that route `0.0.0.0/0` or `::/0`. Warn before activating a
second conflicting full-tunnel profile, or offer to switch profiles cleanly.

### Useful tray menu

List profiles directly in the tray menu with their state and a one-click
connect/disconnect action. Keep the current disconnect-all action.

Core features in this section shipped in 0.2.0 and were refined through 0.3.0.
Recovery is event-driven, so the application does not add a permanent monitoring
daemon. See AUDIT.md for tested behavior and limitations.

## Candidates for later releases

### Optional kill switch

Keep it disabled by default. Activation must be transactional, preserve access
to the VPN endpoint and automatically roll back if the handshake fails. A kill
switch must never strand the user without networking.

### Split tunneling

Start with network-based rules through `AllowedIPs`. Per-application routing
should only be added later if it can be implemented without a privileged,
always-running desktop daemon.

### Profile editor refinements

The validated editor already supports disconnected profiles. A future release
could show a diff before saving and offer structured controls for common fields.

### Portable profile backup

Export an encrypted backup containing selected profiles and application
metadata. Do not implement unencrypted bulk export of private keys.

## Keep outside the core application

- VPN server provisioning and account sales;
- telemetry and analytics;
- an embedded browser;
- advertising, maps or news;
- a permanent speed-test service;
- password storage;
- automatic upload of logs or profiles;
- support for unrelated VPN protocols.

The design rule is simple: minimal interface, strong state handling, predictable
recovery and no hidden background work.
