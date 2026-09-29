# Security and deployment review

## 0.3.0 review - 2026-09-30

Scope: IZtun's GUI, privileged helper, lifecycle, packaging and corresponding
ARM64 engine. This is a focused source review and regression run, not independent
certification or a complete audit of upstream cryptography.

### Corrections

- **High: parser disagreement.** Upstream removes whitespace inside directive
  names. Inputs such as `Fw Mark` and `Allowed IPs` could evade the frontend's
  routing restrictions. Exact ASCII directive names, section allowlists and
  validation again at activation now reject these forms. This prevents the
  confirmed policy bypass; no claim is made that arbitrary code execution was demonstrated.
- Privileged reads reject symlinks, FIFOs, nonregular files, oversized files,
  loose permissions and unexpected owners. Directory validation precedes creation
  of child paths. Socket requests have an absolute deadline, not a resettable
  per-chunk timeout.
- Lock acquisition is bounded. Teardown has a 120-second engine-lock budget and
  a 35-second command budget inside systemd's 180-second stop deadline, avoiding
  the old 45-second stop timeout during concurrent activation.
- A broken profile no longer prevents listing/editing other profiles. Service
  properties are fetched together rather than once per row.
- The GUI limits background jobs, ignores stale results, closes sockets on exit,
  and uses nonblocking, correctly parented dialogs. Diagnostic writes are atomic
  and private. Import reads reject special files and oversized content.
- File pickers explicitly open the current account's home directory. A launch
  from an inaccessible inherited `/root` working directory previously produced
  a GTK permission dialog and blocked automated dialog checks. The fix was
  verified with the same launch context, without granting access to `/root`.
- Release export allowlists sources, excludes live configs/build output and
  checks for recognizable secret patterns and compiled ELF files. Upstream
  public man-page examples are exempted only by exact file hashes. This scanner
  is a guardrail, not a replacement for human release inspection.
- C tools use PIE, RELRO, immediate binding, stack protection and fortification.
  Packages declare the binary's actual libc requirement and include upstream licenses.
- Removed the obsolete machine-specific 0.2.1 deployment script. Supported
  installation is described in README rather than retiring files on a guessed host.

### Validation

- 65 backend/packaging regression tests passed locally and on ARM64.
- 22 GTK tests passed in the Orange Pi's real ARM64 Wayland session.
- The clean source archive built an ARM64 Debian package on Orange Pi.
- The actual Go binary was scanned with `govulncheck v1.8.0`: no vulnerabilities
  reported in called code or imported packages; 30 module-only advisories remain
  outside the executable's called code. This is a dated result, not a guarantee.
- Installed 0.3.0 over 0.2.2 with a root-only backup of the old package and profiles.
  Both user profile hashes remained unchanged. Sources and build tools were retained.
- Installed socket checks as `opi`: Unicode rename, safe edit, stale edit and
  hook rejection passed using a disposable profile.
- Real AWG2 → AWG 3.1 → AWG2 switching authenticated exactly one full tunnel at
  each completed step. An unreachable replacement restored the previous
  authenticated tunnel. Final IPv4/IPv6 routes, policy rules and DNS matched
  the original snapshot. Only disposable profiles were edited/deleted.
- Repair and the recovery service authenticated again. Manual Disconnect was
  respected even with auto-connect temporarily enabled; its original setting
  was restored. Diagnostics omitted keys and the tested peer endpoint.
- List request median was 218-219 ms with two profiles. GUI cgroup memory was
  approximately 73-74 MiB. These are point-in-time measurements, not a claim of
  faster response in every workload or a guaranteed memory ceiling.

### Limits

- Abrupt power loss, forced termination or external modifications can leave
  network state requiring administrator repair; no generic deletion of unrelated
  routing rules is attempted.
- The revised contention budget is regression-tested; arbitrary crash timing
  has not been exhaustively fault-injected.
- Physical suspend, reboot and cable reconnection are not forced during this
  review. No kill switch is provided. Authenticated handshake does not prove
  Internet or DNS reachability.
- Sources include upstream engine/tool code, not OS dependencies or an offline
  Go toolchain/module cache. GitHub CI/provenance is not claimed before it runs.

## Historical 0.2.1 review - 2026-09-28

Scope: version 0.2.1 GTK frontend, root helper, service lifecycle, packaging and
the ARM64 engine shipped to Orange Pi 5. This is not a certification or an audit
of the entire operating system or all upstream cryptographic code.

## Findings corrected

| Finding | Correction |
| --- | --- |
| Root helper opened arbitrary caller-supplied source paths, contrary to the documented boundary | GUI reads a regular `.conf`; helper receives bounded text, never an import path |
| Socket clients could keep root workers waiting indefinitely | Read timeout, request size limit, connection/task/memory/lifetime caps |
| Shell hooks and routing control fields could cross the GUI privilege boundary | Validate at import and activation; reject hooks, option-like names, symlinks, reserved/custom routing tables and marks |
| Boot jobs bypassed the GUI full-tunnel guard | Common engine lock and conflict guard in systemd activation |
| Raw command errors could quote secrets | Fixed command errors; no raw engine stderr or raw errors in exported diagnostics |
| Helper could not write its runtime state under ProtectSystem=strict | Explicit root-only writable runtime directory |
| Existing interface was treated as successful connection | Full tunnels must authenticate within 25 seconds or be torn down |
| Cleanup repeated broad route/rule deletions after awg-quick cleanup | Remove duplicate broad deletions; use checked, serialized lifecycle cleanup and report failures |
| Recovery could reconnect a deliberately disconnected profile | Per-boot manual pause, honoured even with boot autostart enabled |
| Endpoint display parsed the AllowedIPs column | Correct peer dump field mapping |
| Periodic errors opened repeated blocking dialogs; buttons could remain disabled | Inline polling errors, serialized actions, final refresh on both success and failure |
| NetworkManager-only recovery did not cover this Orange Pi | Add networkd-dispatcher routable hook |
| Build used unpatched Go 1.26.0 | Pin patched Go 1.26.8 in Makefile and CI |

## Validation actually performed on ARM64

- 36 regression tests passed, including socket authorization, malformed requests,
  configuration rejection, conflict guards, error redaction and rollback paths.
- Installed the Debian package and called the socket as the unprivileged `opi` user.
- Unreachable disposable endpoint rejected after 25.8 seconds. IPv4/IPv6 routes,
  policy rules and `/etc/resolv.conf` matched the pre-test snapshot after rollback.
- Real AWG2 and AWG 3.1 profiles authenticated; a second full tunnel was rejected.
- Repair authenticated again; Disconnect restored the network snapshot.
- Installed recovery service reauthenticated AWG2. Manual Disconnect remained
  effective with boot autostart temporarily enabled. Original setting restored.
- Both existing profile files retained their SHA-256 hashes through migration.
- GTK window visually checked in the real labwc/Wayland session.
- Median list request latency with two profiles: approximately 0.19-0.20 seconds.
- GUI cgroup memory observed around 80-87 MiB; networkd-dispatcher around 19 MiB.
  These are point-in-time measurements, not guarantees under every workload.

## Dependency scan and its limits

`govulncheck v1.8.0 -mode=binary` on the actual Go 1.26.8 ARM64 executable found
zero vulnerabilities in its code and imported packages at the time of this review.
It still listed 30 advisories against required-module metadata whose vulnerable
code is not called by this executable. A whole-tree `./...` scan also includes
optional Outline/QUIC packages not imported by the shipped command; it must not
be confused with the binary result. Those unused upstream packages were not
rewritten or advertised as fixed.

Official references: [Go release history](https://go.dev/doc/devel/release),
[GO-2026-6090](https://pkg.go.dev/vuln/GO-2026-6090),
[GO-2026-5676](https://pkg.go.dev/vuln/GO-2026-5676).

## Remaining limits

- Fresh handshake proves peer authentication, not DNS or Internet reachability.
- There is no kill switch: failure restores ordinary networking.
- Suspend/resume hooks are installed; physical suspend, cable reconnection and
  reboot were not forced on the user's working desktop. Recovery service itself
  was exercised with a live VPN.
- Automatic recovery uses NetworkManager or networkd-dispatcher and bounded retries.
- Group membership is an administrative network permission; do not grant it to
  untrusted users. Security database scans cannot prove absence of unknown bugs.

## 0.2.2 profile-management validation

- 49 regression tests passed on ARM64. Added Unicode display-name, atomic edit,
  protected backup, stale revision, active-tunnel edit rejection and switch tests.
- Explicit `read-config` now permits authorized group members to read profile
  keys for editing; normal status and diagnostics still omit configuration.
- Installed socket tests as `opi`: renamed and edited a disposable profile,
  rejected shell hooks and stale saves, then removed that test profile.
- Real full tunnels switched AWG2 → AWG 3.1 → AWG2. Exactly one was active and
  authenticated at every completed step. This supersedes GUI conflict rejection
  in 0.2.1; the boot/engine conflict guard still prevents simultaneous full tunnels.
- An unreachable replacement was rejected and the previous AWG2 tunnel
  reauthenticated. Disconnect restored the IPv4/IPv6 routes, rules and DNS snapshot.
- GTK smoke test exercised the actual Rename, Save and Cancel controls with
  synthetic data; final window visually checked in the user's Wayland session.
- Only test profiles were edited. Existing user configurations were not changed.
