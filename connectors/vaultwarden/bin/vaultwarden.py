#!/usr/bin/env python3
"""Vaultwarden helper through the Bitwarden CLI (bw).

Transport is bw itself, not a direct HTTP call with a stored secret.
The CLI already knows the server, the proxy route and the self-signed
certificate. This wrapper only sets that environment and forwards
subcommands, so no credential value ever appears in this file.
"""

import json
import os
import subprocess
import sys

BW = "/home/hatch/.local/bin/bw"
# 同 bw-auto.sh：别用 $HOME，WebSSH 终端里 root 的 HOME=/root，
# 文件实际在 /home/hatch/workspace。
BASE = "/home/hatch" if os.path.isdir("/home/hatch/workspace") else os.path.expanduser("~")
CERT = os.path.join(BASE, "workspace/vaultwarden-lucas-cert.pem")
PROXY = "http://127.0.0.1:7890"


def run_bw(args):
    env = dict(os.environ)
    env["HOME"] = BASE
    env["HTTP_PROXY"] = PROXY
    env["HTTPS_PROXY"] = PROXY
    env["http_proxy"] = PROXY
    env["https_proxy"] = PROXY
    env["NODE_EXTRA_CA_CERTS"] = CERT
    result = subprocess.run(
        [BW] + args,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    if result.stdout:
        sys.stdout.write(result.stdout)
        if not result.stdout.endswith("\n"):
            sys.stdout.write("\n")
    if result.stderr:
        sys.stderr.write(result.stderr)
    return result.returncode


def main():
    if len(sys.argv) < 2:
        print("usage: vaultwarden.py <status|login-check|unlock-check|sync|list|get-password|get-username|get-item> [args]", file=sys.stderr)
        return 2
    cmd = sys.argv[1]
    rest = sys.argv[2:]
    session = os.environ.get("BW_SESSION")
    if not session:
        # 全自动模式：复用 bw-auto.sh 缓存的 session（600 文件，只含 session key，
        # 不含主密码）。没有缓存时这里不自动解锁，交给 bw-auto.sh 去读 bw.env。
        try:
            with open(os.path.join(BASE, "workspace/.credentials/bw-session")) as f:
                session = f.read().strip() or None
        except OSError:
            session = None
    session_args = ["--session", session] if session else []

    if cmd == "status":
        return run_bw(["status"])
    if cmd == "login-check":
        return run_bw(["login", "--check"])
    if cmd == "unlock-check":
        return run_bw(["unlock", "--check"])
    if cmd == "sync":
        return run_bw(["sync"] + session_args)
    if cmd == "list":
        # vaultwarden.py list [--search text] [--url url]
        return run_bw(["list", "items"] + session_args + rest)
    if cmd == "get-password":
        if not rest:
            print("usage: vaultwarden.py get-password <name-or-id>", file=sys.stderr)
            return 2
        return run_bw(["get", "password", rest[0]] + session_args)
    if cmd == "get-username":
        if not rest:
            print("usage: vaultwarden.py get-username <name-or-id>", file=sys.stderr)
            return 2
        return run_bw(["get", "username", rest[0]] + session_args)
    if cmd == "get-item":
        if not rest:
            print("usage: vaultwarden.py get-item <name-or-id>", file=sys.stderr)
            return 2
        return run_bw(["get", "item", rest[0]] + session_args)
    print(f"unknown command: {cmd}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
