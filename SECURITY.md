# Security policy

## Supported version

Only the latest tagged release is supported.

## Reporting a vulnerability

Please do not publish a working exploit, private VPN configuration, key, IP
address or customer information in a public issue. Use GitHub's **Security →
Report a vulnerability** function to open a private security advisory.

## Security boundaries

- The graphical application is unprivileged.
- Administrative operations go through a root-owned Unix socket.
- Access is limited to members of the `amneziawg` system group.
- The helper obtains the real caller UID from `SO_PEERCRED`; it does not trust
  a username sent by the GUI.
- The unprivileged GUI reads a regular `.conf` file and sends its contents.
  The root helper accepts no source file paths. Payloads are capped at 64 KiB;
  socket requests, request read time, connections, tasks and memory are bounded.
- Shell hooks (`PreUp`, `PostUp`, `PreDown`, `PostDown`) and `SaveConfig` are
  rejected during import.
- Profiles are stored as root-only files under `/etc/amneziawg`.
- Authorized group members can explicitly read profile secrets in the editor.
  Status and diagnostics do not return config text. Treat group membership as
  permission to read every VPN profile, not just toggle its connection.
- Configuration edits require an inactive tunnel, use the engine lock, validate
  content, check the original revision and atomically replace mode-0600 files.
  One protected previous version is retained. Display-name changes leave
  interface identifiers and connection settings untouched.
- Interface names cannot begin with an option marker; symlink profiles, custom
  routing tables and custom firewall marks are rejected.
- Directive names must use exact supported ASCII spellings; internal whitespace
  cannot disguise a privileged routing option. Validation also runs at activation.
- Privileged reads are bounded, nonblocking and restricted to regular root-owned
  private files. Invalid configurations do not block the entire profile list.
- The same locked activation guard runs for GUI actions and systemd boot jobs.
- Engine stderr is never forwarded to the GUI or exported in diagnostics.
- Diagnostic exports omit profile names, endpoints, raw logs and configuration.

This is a source review and regression suite, not a claim that every possible
vulnerability in the OS, upstream engine or desktop stack has been eliminated.

Membership in the `amneziawg` group grants permission to establish VPN
tunnels and alter the machine's routes and DNS. Treat that group as an
administrative privilege.
