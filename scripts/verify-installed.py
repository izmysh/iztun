#!/usr/bin/python3
"""Opt-in integration checks on an installed system; run as the GUI user.

--rollback temporarily creates an unreachable, disposable full tunnel. Run only
when no real VPN is active. --live PROFILE connects, repairs and disconnects it.
No private keys or endpoint addresses are printed.
"""
import argparse
import json
import socket
import subprocess
import time
from pathlib import Path


def request(*args):
    with socket.socket(socket.AF_UNIX) as client:
        client.settimeout(420)
        client.connect("/run/amneziawg-linux-gui.sock")
        client.sendall(json.dumps({"args": list(args)}).encode())
        client.shutdown(socket.SHUT_WR)
        data = bytearray()
        while chunk := client.recv(65536):
            data.extend(chunk)
    return json.loads(data)


def ok(*args):
    result = request(*args)
    if not result["ok"]:
        raise RuntimeError(result["error"])
    return result["output"]


def snapshot():
    return [subprocess.check_output(["ip", family, what, "show"], text=True)
            for family in ("-4", "-6") for what in ("rule", "route")] + [Path("/etc/resolv.conf").read_text()]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--rollback", action="store_true")
    parser.add_argument("--live")
    parser.add_argument("--recovery", help="Root-only service/hook integration test for a real profile")
    args = parser.parse_args()
    samples = []
    for _ in range(5):
        start = time.monotonic()
        profiles = json.loads(ok("list"))
        samples.append(time.monotonic() - start)
    print(f"List latency: median {sorted(samples)[2]*1000:.0f} ms")
    print("Profiles:", [(p["name"], p["health"]) for p in profiles])
    assert not request("import", "/etc/shadow", "auditblocked")["ok"]
    assert not request("recover")["ok"]
    print("Privileged path import and root-only command denied: OK")

    if args.rollback:
        assert not any(p["active"] for p in profiles), "Disconnect VPNs before the rollback test"
        name = "awg-audit-test"
        assert all(p["name"] != name for p in profiles)
        before = snapshot()
        private = subprocess.check_output(["awg", "genkey"], text=True).strip()
        peer_private = subprocess.check_output(["awg", "genkey"], text=True)
        public = subprocess.check_output(["awg", "pubkey"], input=peer_private, text=True).strip()
        config = (f"[Interface]\nPrivateKey = {private}\nAddress = 10.250.240.2/32\nDNS = 1.1.1.1\n"
                  f"[Peer]\nPublicKey = {public}\nAllowedIPs = 0.0.0.0/0\nEndpoint = 127.0.0.1:9\n")
        ok("import", config, name)
        try:
            start = time.monotonic()
            result = request("up", name)
            assert not result["ok"], "Unreachable peer incorrectly accepted"
            print(f"Unreachable server rejected in {time.monotonic()-start:.1f}s: {result['error']}")
            assert snapshot() == before, "Routes/rules/DNS differ after rollback"
            print("Rollback restored IPv4/IPv6 routes, policy rules and DNS: OK")
        finally:
            ok("delete", name)

    if args.live:
        name = args.live
        before = snapshot()
        try:
            ok("up", name)
            record = next(p for p in json.loads(ok("list")) if p["name"] == name)
            assert record["health"] == "connected", record["health"]
            print("Live VPN authenticated handshake: OK")
            others = [p for p in profiles if p["full_tunnel"] and p["name"] != name]
            if others:
                other = others[0]["name"]
                try:
                    ok("up", other)
                    records = json.loads(ok("list"))
                    assert next(p for p in records if p["name"] == other)["health"] == "connected"
                    assert not next(p for p in records if p["name"] == name)["active"]
                    ok("up", name)
                    print("Full-tunnel switching in both directions: OK")
                finally:
                    ok("down", other)
            report = ok("diagnostics", name)
            assert record["endpoint"] not in report if record["endpoint"] else True
            assert "PrivateKey" not in report and "PresharedKey" not in report
            ok("repair", name)
            record = next(p for p in json.loads(ok("list")) if p["name"] == name)
            assert record["health"] == "connected"
            print("Repair reauthenticated the peer; diagnostics omit endpoint and keys: OK")
        finally:
            ok("down", name)
        assert snapshot() == before, "Network state differs after Disconnect"
        print("Disconnect restored network state: OK")

    if args.recovery:
        name = args.recovery
        record = next(p for p in profiles if p["name"] == name)
        was_enabled = record["enabled"]
        before = snapshot()
        try:
            ok("up", name)
            subprocess.run(["systemctl", "start", "amneziawg-recover.service"], check=True, timeout=180)
            record = next(p for p in json.loads(ok("list")) if p["name"] == name)
            assert record["health"] == "connected"
            print("Recovery service reauthenticated live tunnel: OK")
            ok("autostart", name, "on")
            ok("down", name)
            # Ensure debounce does not turn this into a false positive.
            time.sleep(6)
            subprocess.run(["systemctl", "start", "amneziawg-recover.service"], check=True, timeout=180)
            record = next(p for p in json.loads(ok("list")) if p["name"] == name)
            assert not record["active"] and record["enabled"]
            print("Manual Disconnect respected despite boot autostart: OK")
        finally:
            ok("down", name)
            ok("autostart", name, "on" if was_enabled else "off")
        assert snapshot() == before
        print("Recovery test restored original network and boot preference: OK")


if __name__ == "__main__":
    main()
