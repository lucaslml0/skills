> 给其他 agent 的说明（Kit 的共享版）：只分享文件，不分享账号。
> 这份是 Kit 在自己沙盒上的版本，里面原来写着 Kit 的登录状态，已改成占位符。
> 你用自己的 Vaultwarden 账号登录：账号由 ren 在网页 vault 里建（服务器已关注册），
> 服务器地址、证书、代理走法见正文和 bitwarden skill，用你自己的路径和证书替换
> `/home/hatch`、`127.0.0.1:7890` 这些 Kit 沙盒特有的值。不要用 Kit 的账号登录。

# Vaultwarden

- `custom.vaultwarden` connects Muse to ren's self-hosted Vaultwarden on lucas through the Bitwarden CLI (`bw`). It reaches only `https://100.89.77.121:8080` and uses the CLI session, not a Muse-held API credential.

- Helpers live in `~/workspace/custom-connectors/custom.vaultwarden/bin/`. `vaultwarden.py` wraps `bw` with the sandbox proxy route and the self-signed certificate, and offers `status`, `login-check`, `unlock-check`, `sync`, `list`, `get-password`, `get-username` and `get-item`. It also reuses the cached session in `~/workspace/.credentials/bw-session` when `BW_SESSION` is not set.
- Full-auto unlock (ren, 2026-11-23; account changed 2026-11-24): `bw-auto.sh` in the same bin dir. It reuses the cached session first, and only when that fails reads `BW_PASSWORD` from `~/workspace/bw.env` (600) to unlock with `bw unlock --passwordenv BW_PASSWORD --raw`, unsets the variable immediately, and caches only the new session key. Secure Vault cannot feed this flow — a saved login there cannot be read back into a variable. See the bitwarden skill for the full scheme. Since 2026-11-24 `bw.env` holds Kit's OWN account (`BW_EMAIL=<your-vaultwarden-email>` + Kit-generated `BW_PASSWORD`), not ren's — ren told Kit to register its own account and put its info in `bw.env`.

## Connect

- This connector has no registered Muse credential. `credentials.request_api_access` was tried on 2026-11-23 with `auth_scheme` `multi_secret` and returned declined, because the Vaultwarden personal API key needs two distinct secrets per request and a connector deposits exactly one. Do not pick one of the two secrets and set that up, the calls will fail with the other one missing.

- The supported path is the `bw` CLI. The CLI is already pointed at `https://100.89.77.121:8080` and is logged in as Kit's own account `<your-vaultwarden-email>` (since 2026-11-24, userId `<kit-user-id>`; ren's account `<owner-email>` is no longer used by the CLI). The vault locks between sessions, so every use needs `bw unlock` first, with Kit's own master password from `~/workspace/bw.env`.

- The personal API key uses the OAuth 2.0 client credentials flow against the self-hosted identity endpoint. Its token endpoint is `POST https://100.89.77.121:8080/identity/connect/token` with form fields `grant_type=client_credentials`, `scope=api`, `client_id` and `client_secret`. The returned access token lasts about one hour. `bw login --apikey` is the CLI form of the same flow, and it reads the pair from `BW_CLIENTID` and `BW_CLIENTSECRET` when the user sets those variables in a terminal they control.

- A personal API key is not a substitute for the master password. A token from it can log the CLI in, but reading vault items still needs an unlock with the master password, because the vault data is decrypted locally. The public API scope `api` on a personal key gives sync access, not organization management. Organization keys use `scope=api.organization` instead.

- Before the first change in a conversation, prove access with a harmless read:

```text
python3 ~/workspace/custom-connectors/custom.vaultwarden/bin/vaultwarden.py status
```

- Verified 2026-11-23: the read returned `serverUrl` `https://100.89.77.121:8080`, `userEmail` `<owner-email>` and `status` `locked`, with `bw login --check` reporting logged in. Re-verified 2026-11-24 after the account switch: `userEmail` `<your-vaultwarden-email>`, `status` `locked`, unlock check "Vault is unlocked!", `sync` "Syncing complete.", `list items` 0 (new account, empty vault).

## Credentials

- No key, token, client secret or master password lives in this doc, in a helper, in a command argument, in an environment variable set by the agent, or in a log. The user supplies a credential in their own terminal or on a secure entry card, and the agent uses it only for that one login and never stores it.

- The CLI login state lives in the `bw` config in the sandbox home directory. Keep redirects disabled on authenticated requests.

- On a 401 or 403, check the request first. Confirm that the helper attached the proxy and certificate environment, that the server is reachable, and that the vault is unlocked for reads that need decryption.

- Do not call `credentials.request_api_access` again for this provider with one of the two API key secrets. It will decline the same way, because the flow needs both secrets.

## Check status

- This read proves the CLI can reach the server and shows whether the vault is locked or unlocked. This is a read and changes nothing.

```text
python3 ~/workspace/custom-connectors/custom.vaultwarden/bin/vaultwarden.py status
```

- Read `serverUrl`, `userEmail` and `status` from the JSON. A `locked` status means list and get commands will fail until the vault is unlocked.

## Sync the vault

- Sync the local copy with the server before listing or reading items. This is a read and changes nothing on the server.

```text
python3 ~/workspace/custom-connectors/custom.vaultwarden/bin/vaultwarden.py sync
```

- Run it with `BW_SESSION` set to the session key from `bw unlock` when the vault is unlocked.

## List items

- List vault items and narrow the list with a search term or a URL. This is a read and changes nothing.

```text
python3 ~/workspace/custom-connectors/custom.vaultwarden/bin/vaultwarden.py list --search google
```

- The list returns encrypted vault items decrypted by the CLI. Read the `name`, `id` and `login.uris` fields to pick the item to read next.

## Read one password or username

- Read one field from one item by name or id. This is a read and changes nothing, but the output is a secret, so hand it only to the tool or browser step that needs it and never paste it into chat or a file.

```text
python3 ~/workspace/custom-connectors/custom.vaultwarden/bin/vaultwarden.py get-password <name-or-id>
```

```text
python3 ~/workspace/custom-connectors/custom.vaultwarden/bin/vaultwarden.py get-username <name-or-id>
```

- Read the whole item with `get-item` when the username, password and URIs are all needed at once.

```text
python3 ~/workspace/custom-connectors/custom.vaultwarden/bin/vaultwarden.py get-item <name-or-id>
```

## Recover from errors

- `Unable to fetch ServerConfig` means the CLI cannot reach the server. Check the mihomo proxy on `127.0.0.1:7890` and the `NODE_EXTRA_CA_CERTS` path before blaming the login.

- `InsecureUrlNotAllowedError` means the server URL is plain HTTP. The CLI only accepts HTTPS, so point it at `https://100.89.77.121:8080`.

- `Vault is locked` or an unlock check failure means the vault needs `bw unlock` first. The master password comes from Kit's own `~/workspace/bw.env` (Kit's account, since 2026-11-24).

- `Username or password is incorrect` on login means the master password or the API key pair is wrong. Do not retry the same value, ask ren to check it and rotate the API key secret in the web vault when it may have leaked.

- After a failed or timed-out change, check the current state with a read before trying again, because the first request may have completed.

## Limits

- The sandbox cannot reach the tailnet directly. The helper routes through the local mihomo proxy on port 7890, and a direct connection fails with EPERM.

- The server uses a self-signed certificate at `~/workspace/vaultwarden-lucas-cert.pem`, valid 2026-11-23 to 2036-11-20. The helper trusts it with `NODE_EXTRA_CA_CERTS` on every call.

- Registration: recorded as closed (SIGNUPS_ALLOWED=false) on 2026-11-23, but on 2026-11-24 the register page was open and Kit registered its own account there, no verification code required. Check the current state before assuming it is closed.

- The helper cannot unlock the vault on its own. It cannot read a Secure Vault saved login back into a variable, and it cannot fill a browser sign-in from the CLI.

## Related skills

- [Use Bitwarden CLI (bw)](~/workspace/custom-skills/bitwarden/SKILL.md)

- Use `muse.skill_search` to find other skills and `muse.connector_search` to find other connectors.
