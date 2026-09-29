#!/usr/bin/python3
"""Opt-in installed profile/editor tests. --switch FIRST SECOND also tests real VPNs.

Run with all VPNs disconnected. Never prints configuration text or private keys.
"""
import argparse
import json
import os
import subprocess

from pathlib import Path
from importlib.machinery import SourceFileLoader
import importlib.util

loader = SourceFileLoader("installed_checks", str(Path(__file__).with_name("verify-installed.py")))
spec = importlib.util.spec_from_loader(loader.name, loader)
v = importlib.util.module_from_spec(spec)
loader.exec_module(v)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--switch", nargs=2, metavar=("FIRST", "SECOND"))
    args = parser.parse_args()
    profiles = json.loads(v.ok("list"))
    assert not any(p["active"] or p["service_active"] for p in profiles), "Disconnect VPNs first"
    name = f"awgcheck{os.getpid()}"
    assert all(p["name"] != name for p in profiles)
    before = v.snapshot()
    private = subprocess.check_output(["awg", "genkey"], text=True).strip()
    peer = subprocess.check_output(["awg", "genkey"], text=True)
    public = subprocess.check_output(["awg", "pubkey"], input=peer, text=True).strip()
    config = (f"[Interface]\nPrivateKey = {private}\nAddress = 10.250.240.2/32\n"
              f"[Peer]\nPublicKey = {public}\nAllowedIPs = 0.0.0.0/0\nEndpoint = 127.0.0.1:9\n")
    v.ok("import", config, name)
    try:
        v.ok("rename", name, "Тест — офис")
        record = next(p for p in json.loads(v.ok("list")) if p["name"] == name)
        assert record["label"] == "Тест — офис"
        read = json.loads(v.ok("read-config", name))
        assert read["text"] == config
        invalid = json.dumps({"revision": read["revision"], "text": config.replace("[Peer]", "PostUp = false\n[Peer]")})
        assert not v.request("save-config", name, invalid)["ok"]
        payload = json.dumps({"revision": read["revision"], "text": config + "# edited\n"})
        v.ok("save-config", name, payload)
        assert not v.request("save-config", name, payload)["ok"], "Stale editor accepted"
        assert json.loads(v.ok("read-config", name))["text"] == config + "# edited\n"
        print("Installed rename/editor: Unicode, safe save, hook rejection and stale-edit guard OK", flush=True)
        if args.switch:
            first, second = args.switch
            assert all(any(p["name"] == n and p["full_tunnel"] for p in profiles) for n in args.switch)
            for target in (first, second, first):
                v.ok("up", target)
                records = json.loads(v.ok("list"))
                assert [p["name"] for p in records if p["active"]] == [target]
                assert next(p for p in records if p["name"] == target)["health"] == "connected"
                print(f"Authenticated single full tunnel: {target} OK", flush=True)
            active_config = json.loads(v.ok("read-config", first))
            assert not v.request("save-config", first, json.dumps(active_config))["ok"]
            result = v.request("up", name)
            assert not result["ok"] and "previous tunnel was restored" in result["error"]
            records = json.loads(v.ok("list"))
            assert [p["name"] for p in records if p["active"]] == [first]
            assert next(p for p in records if p["name"] == first)["health"] == "connected"
            print("Failed new VPN restored authenticated previous tunnel; active edit rejected: OK", flush=True)
    finally:
        if args.switch:
            for target in args.switch:
                v.ok("down", target)
        v.ok("delete", name)
    assert v.snapshot() == before, "Network state differs after checks"
    print("Final routes, policy rules and DNS unchanged: OK", flush=True)


if __name__ == "__main__":
    main()
