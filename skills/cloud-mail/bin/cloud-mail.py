#!/usr/bin/env python3
"""Cloud Mail API helper for ren's mail.520141025.xyz (maillab/cloud-mail).

Auth is POST /api/login with an email + password, which returns a token.
Every other call sends that token raw in the `Authorization` header
(no "Bearer " prefix).

Two quirks of this deployment, both verified 2026-11-24:
  1. The token check is flaky: the same valid token returns 200 or
     401 ("身份认证失效,请重新登录") at random on repeated calls.
     So every call retries, re-logging in on 401.
  2. Python's default User-Agent is blocked by Cloudflare, and the
     connection sometimes drops (RemoteDisconnected). Always send a
     browser User-Agent and retry transport errors.

Credentials come from Bitwarden, never from this file:
  - Default item: `cloud-mail-ikcuhjve` in the Vaultwarden org `lucas`,
    collection `mail` (username + password read with bw-auto.sh).
  - Override with --item <name>, or env CLOUD_MAIL_BW_ITEM.
  - Or set CLOUD_MAIL_EMAIL / CLOUD_MAIL_PASSWORD in your own terminal.
  - Last fallback (Kit's sandbox only): the 600 credential file
    ~/workspace/.credentials/cloud-mail-ikcuhjve.json.

The helper never prints the password or the token.

Usage:
  cloud-mail.py whoami
  cloud-mail.py accounts
  cloud-mail.py emails [--account-id N] [--size N] [--type 0|1] [--full 0|1]
  cloud-mail.py add-account <new@520141025.xyz>
  cloud-mail.py delete-account <accountId>
  cloud-mail.py send --to a@x.com [--to b@x.com] --subject S --content '<div>..</div>' [--text ..]
  cloud-mail.py delete-email <emailId>[,<emailId>...]
  cloud-mail.py admin-users [--email PREFIX]
  cloud-mail.py admin-add-user <email>   (prompts for the password on stdin, no echo)
  cloud-mail.py regkeys
"""

import argparse
import getpass
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

BASE = os.environ.get("CLOUD_MAIL_BASE", "https://mail.520141025.xyz")
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36"
BW_AUTO = os.environ.get(
    "BW_AUTO_SH",
    "/home/hatch/workspace/custom-connectors/custom.vaultwarden/bin/bw-auto.sh",
)
DEFAULT_ITEM = os.environ.get("CLOUD_MAIL_BW_ITEM", "cloud-mail-ikcuhjve")


def bw_get(field, item):
    """Read one field from a bw item via bw-auto.sh. Returns None on failure."""
    cmd = BW_AUTO if os.path.exists(BW_AUTO) else "bw"
    try:
        r = subprocess.run(
            [cmd, "get", field, item],
            capture_output=True, text=True, timeout=90,
        )
    except Exception:
        return None
    out = r.stdout.strip()
    return out or None


def credentials(item):
    """Resolve (email, password) without ever printing either value."""
    email = os.environ.get("CLOUD_MAIL_EMAIL")
    password = os.environ.get("CLOUD_MAIL_PASSWORD")
    if email and password:
        return email, password
    if email is None:
        email = bw_get("username", item)
    if password is None and email:
        password = bw_get("password", item)
    if email and password:
        return email, password
    # Kit sandbox fallback: a local 600 credential file.
    for name in ("cloud-mail-ikcuhjve.json",):
        p = Path.home() / "workspace" / ".credentials" / name
        try:
            d = json.loads(p.read_text())
        except Exception:
            continue
        if d.get("email") and d.get("password"):
            return d["email"], d["password"]
    return None, None


def raw(method, path, token=None, body=None, tries=4):
    for _ in range(tries):
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(BASE + path, data=data, method=method)
        req.add_header("User-Agent", UA)
        if body is not None:
            req.add_header("Content-Type", "application/json")
        if token:
            req.add_header("Authorization", token)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            try:
                return json.loads(e.read() or b"{}")
            except Exception:
                return {"code": e.code, "message": "non-JSON error response"}
        except Exception:
            time.sleep(3)
    return {"code": None, "message": "transport failed after retries"}


def login(email, password):
    for _ in range(6):
        b = raw("POST", "/api/login", body={"email": email, "password": password})
        tok = (b.get("data") or {}).get("token")
        if tok:
            return tok
        time.sleep(3)
    return None


class Client:
    def __init__(self, email, password):
        self.email = email
        self.password = password

    def call(self, method, path, body=None, attempts=6):
        """One API call, re-logging in whenever the server answers 401."""
        last = {"code": None, "message": "no attempt made"}
        for i in range(attempts):
            tok = login(self.email, self.password)
            if not tok:
                return {"code": None, "message": "login failed"}
            last = raw(method, path, token=tok, body=body)
            if last.get("code") == 200:
                return last
            time.sleep(3)
        return last


def fail(msg, code=2):
    print(f"cloud-mail: {msg}", file=sys.stderr)
    raise SystemExit(code)


def main():
    global BASE
    ap = argparse.ArgumentParser(description="Cloud Mail API helper")
    ap.add_argument("--item", default=DEFAULT_ITEM,
                    help="bw item holding the Cloud Mail account (default: %(default)s)")
    ap.add_argument("--base", default=BASE, help="Cloud Mail base URL")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("whoami", help="GET /api/my/loginUserInfo")
    sub.add_parser("accounts", help="GET /api/account/list")
    em = sub.add_parser("emails", help="GET /api/email/list")
    em.add_argument("--account-id", type=int, required=True)
    em.add_argument("--size", type=int, default=10)
    em.add_argument("--type", type=int, default=0, help="0 received, 1 sent")
    em.add_argument("--full", type=int, default=0)
    aa = sub.add_parser("add-account", help="POST /api/account/add")
    aa.add_argument("email")
    da = sub.add_parser("delete-account", help="DELETE /api/account/delete")
    da.add_argument("account_id", type=int)
    se = sub.add_parser("send", help="POST /api/email/send")
    se.add_argument("--account-id", type=int, required=True)
    se.add_argument("--to", dest="to", action="append", required=True)
    se.add_argument("--subject", required=True)
    se.add_argument("--content", required=True, help="HTML body")
    se.add_argument("--text", default="")
    se.add_argument("--name", default="")
    de = sub.add_parser("delete-email", help="DELETE /api/email/delete")
    de.add_argument("email_ids", help="comma-separated email ids")
    au = sub.add_parser("admin-users", help="GET /api/user/list (admin)")
    au.add_argument("--email", default="")
    aau = sub.add_parser("admin-add-user", help="POST /api/user/add (admin)")
    aau.add_argument("email")
    sub.add_parser("regkeys", help="GET /api/regKey/list (admin)")

    args = ap.parse_args()
    BASE = args.base.rstrip("/")

    email, password = credentials(args.item)
    if not email or not password:
        fail(f"no Cloud Mail credentials: bw item '{args.item}' has no usable "
             "username/password and CLOUD_MAIL_EMAIL/CLOUD_MAIL_PASSWORD are unset. "
             "Put the @520141025.xyz account into the bw lucas org mail collection first.")
    client = Client(email, password)

    if args.cmd == "whoami":
        b = client.call("GET", "/api/my/loginUserInfo")
    elif args.cmd == "accounts":
        b = client.call("GET", "/api/account/list?size=30")
    elif args.cmd == "emails":
        b = client.call("GET", f"/api/email/list?accountId={args.account_id}"
                               f"&type={args.type}&size={args.size}&full={args.full}")
    elif args.cmd == "add-account":
        b = client.call("POST", "/api/account/add", body={"email": args.email})
    elif args.cmd == "delete-account":
        b = client.call("DELETE", f"/api/account/delete?accountId={args.account_id}")
    elif args.cmd == "send":
        body = {"accountId": args.account_id, "receiveEmail": args.to,
                "subject": args.subject, "content": args.content,
                "text": args.text, "sendType": ""}
        if args.name:
            body["name"] = args.name
        b = client.call("POST", "/api/email/send", body=body)
        if b.get("code") == 403:
            print("Note: this Cloud Mail instance has sending disabled "
                  "(403 邮件发送功能已停用). Re-enable sending in the admin "
                  "settings before send can work.", file=sys.stderr)
    elif args.cmd == "delete-email":
        b = client.call("DELETE", f"/api/email/delete?emailIds={args.email_ids}")
    elif args.cmd == "admin-users":
        q = f"?num=1&size=50&email={args.email}" if args.email else "?num=1&size=50"
        b = client.call("GET", f"/api/user/list{q}")
    elif args.cmd == "admin-add-user":
        pw = getpass.getpass(f"Password for new user {args.email} (min 6 chars): ")
        if len(pw) < 6:
            fail("password must be at least 6 characters")
        b = client.call("POST", "/api/user/add",
                        body={"email": args.email, "password": pw})
    elif args.cmd == "regkeys":
        b = client.call("GET", "/api/regKey/list")
    else:
        fail(f"unknown command {args.cmd}")

    print(json.dumps(b, ensure_ascii=False, indent=2))
    raise SystemExit(0 if b.get("code") == 200 else 1)


if __name__ == "__main__":
    main()
