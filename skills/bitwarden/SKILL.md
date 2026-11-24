# Use Bitwarden CLI (bw)

## Install bw

- Install the CLI with npm into the home directory, so it survives sandbox rebuilds.

- Run `npm install -g @bitwarden/cli --prefix ~/.npm-global` and link it with `ln -sf ~/.npm-global/bin/bw ~/.local/bin/bw`. The `--prefix` matters: npm's default global prefix here is `/usr`, so without it the install lands in `/usr/lib/node_modules` and `~/.local/bin/bw` keeps pointing at the old version — verify with `grep '"version"' ~/.npm-global/lib/node_modules/@bitwarden/cli/package.json`, not just `npm ls -g`.

- Check the install with `bw --version`. Version 2025.12.0 is the one verified working on 2026-11-24. Do NOT use 2026.11.0: it silently swallows unlock/sync errors (exit code 0, zero output), while 2025.12.0 reports the real error (see Troubleshooting).

- The `~/.local/bin` directory is on PATH in interactive shells. In a plain exec shell call the full path `/home/hatch/.local/bin/bw`.

## Point bw at the server

- Point the CLI at a server with `bw config server <url>`. Check it with `bw status`, which prints the server URL and the login state.

- The CLI refuses plain HTTP. An HTTP URL fails with InsecureUrlNotAllowedError, so the server URL must use HTTPS.

- A self signed server certificate fails validation until Node trusts it. Set `NODE_EXTRA_CA_CERTS` to the certificate file path on every bw call that talks to the server.

- The CLI prints `Unable to fetch ServerConfig` with a proxy or certificate error when it cannot reach the server. Read that error before blaming the login.

## Reach the server from the sandbox

- The sandbox blocks direct outbound TCP, so point bw at the local mihomo proxy instead of the default egress proxy.

- For ren's Vaultwarden on the tailnet, run bw with `HTTP_PROXY=http://127.0.0.1:7890 HTTPS_PROXY=http://127.0.0.1:7890 http_proxy=http://127.0.0.1:7890 https_proxy=http://127.0.0.1:7890 NODE_EXTRA_CA_CERTS=$HOME/workspace/vaultwarden-lucas-cert.pem`.

- The default egress proxy cannot reach tailnet addresses, and a direct connection fails with EPERM. The local mihomo proxy on port 7890 reaches the tailnet.

- Verify the route with `bw status` before logging in. A clean JSON reply with no fetch error means the server is reachable.

## Log in and unlock

- Log in with `bw login`. It asks for the email and the master password, and it prints a session key with `--raw`.

- Never put the USER's master password in a command argument, an environment variable, a file, a log or a chat message. Let the user type it at the prompt, or use `--passwordenv` with a variable the user set, or `--passwordfile` with a 600 file the user wrote. Exception: Kit's OWN generated account password lives in `~/workspace/bw.env` (600) by ren's explicit instruction (see 全自动解锁) — that is Kit's credential, not the user's, and it still never goes into chat, logs or memory.

- Ask the user for the master password only when the task genuinely needs a login. Offer the Secure Vault card first, and use a password the user sends in chat only for that one login and never store it.

- Unlock the vault with `bw unlock`. It prints a session key, so export it as `BW_SESSION` for later commands in the same shell.

- An unlock invalidates earlier session keys. Run `bw lock` when the work is done, and run `bw logout` to end the login entirely.

- Check the state with `bw login --check` and `bw unlock --check` before you assume a command will work.

- Log in with a personal API key with `bw login --apikey`. It prompts for the `client_id` and `client_secret` from Settings → Security → Keys in the web vault, and it uses the OAuth 2.0 client credentials flow with `grant_type=client_credentials` and `scope=api` against `https://100.89.77.121:8080/identity/connect/token`. In an automated shell the user sets `BW_CLIENTID` and `BW_CLIENTSECRET` in a terminal they control. An API key is not a substitute for the master password, reading vault items still needs `bw unlock` afterwards.

## 全自动解锁（ren 2026-11-23 定的方案；账号 2026-11-24 已换成 Kit 自己的）

- 安全存储（Secure Vault）里存的登录**读不回明文**，所以全自动走不了那条路，只能走下面这个你自己填的文件。
- `~/workspace/bw.env`（600）：2026-11-24 起里面是 Kit 自己的账号，`BW_EMAIL=kit@<your-domain>` + `BW_PASSWORD=`（Kit 生成的 24 字符主密码，ren 11 月 24 日让 Kit 注册自己的账号并把信息存进 bw.env）。此前是 ren 自己填他账号的主密码，那套已废弃；Kit 的旧账号 <owner-email> 不再由 CLI 使用。Kit 不把密码值发进聊天、日志或记忆。
- 包装器 `~/workspace/custom-connectors/custom.vaultwarden/bin/bw-auto.sh`（700），路径一律按 `/home/hatch/workspace` 算，不用 `$HOME`：WebSSH root 终端里 `HOME=/root`，用 `$HOME` 会走到不存在的 `/root/workspace`，bw 自己的登录状态也会丢。WebSSH 终端里直接跑全路径，不用先 source `bw.env`：
  1. 先读 `~/workspace/.credentials/bw-session` 里的缓存 session，用 `bw unlock --check --session` 验一下，还有效就直接用，全程不碰主密码。
  2. session 失效/没有时，才读 `bw.env` 的 `BW_PASSWORD`，用 `bw unlock --passwordenv BW_PASSWORD --raw` 拿新 session，立刻 `unset BW_PASSWORD`，再把新 session（不是主密码）写进 `bw-session`（600）下次复用。
  3. 两条都走不通就报错退出，不用空密码重试。
- 用法就是把 `bw` 换成 `bw-auto.sh`：`bw-auto.sh list items --search google`、`bw-auto.sh get password google1`、`bw-auto.sh sync`。`bw-auto.sh status` 不用解锁。`bw-auto.sh lock` 锁 vault 并丢弃 session；`bw-auto.sh forget` 再把 `bw.env` 清空回模板。
- 小心 `bw-auto.sh` 的一个坑：它解锁失败（空 session）时仍会把空串写进 `bw-session`，盖掉原来好的 session，之后 `bw` 可能卡在交互式 `? Master password:` 提示上等输入。遇上就杀掉进程（不要往提示里输密码），跑 `bw-auto.sh unlock --check` 重建 session，再重试。
- `bw unlock` 会让旧 session 失效，所以每次重新解锁都会覆盖 `bw-session`，这是正常的。
- 更安全的一档（可选）：第一次解锁成功后，把 `bw.env` 里的密码清空，只留 session 缓存——主密码就不在磁盘上了，全自动一直有效到 session 失效（锁 vault / 登出）为止，失效后再填一次密码。

## Pass the password with variables

- Give bw the password through a variable with `bw login --passwordenv BW_PASSWORD` or `bw unlock --passwordenv BW_PASSWORD`. The CLI reads the value from the named variable and never sees it as an argument.

- Set the variable in a terminal the user controls, or let the user type the password at the interactive prompt. The agent never writes a credential value into a variable, a file, a log or a command.

- A login saved through the Secure Vault card cannot be read back into a variable. The agent can confirm the saved login exists, but it cannot see or read the stored values, and the card exists to fill browser sign-ins.

- When the work is done, clear the variable with `unset BW_PASSWORD` so the value does not linger in that shell. Never reuse a password the user sent for one login on a later command.

## Read passwords

- Sync first with `bw sync` so the local copy matches the server.

- List items with `bw list items` and narrow it with `--search <text>` or `--url <url>`.

- Read one field with `bw get password <name or id>` or `bw get username <name or id>`. Read the whole item with `bw get item <name or id>`.

- Pass the session key with `--session $BW_SESSION` when the command runs outside the shell that unlocked the vault.

- Never print a password into a reply, a file, a log or a transcript unless the user asked for that exact value. Hand it to the tool or the browser step that needs it.

## Save passwords

- Make a new password with `bw generate --length 20 --uppercase --lowercase --number --special`, or a passphrase with `bw generate --passphrase --words 5`.

- Build a new item from the template with `bw get template item`, fill in the name, the login URI, the username and the password, then pipe it through `bw encode` into `bw create item`.

- Change an item by fetching it with `bw get item <id>`, editing the JSON, then piping it through `bw encode` into `bw edit item <id>`.

- Run `bw sync` after a create or an edit so the server holds the change.

- Save new accounts into Bitwarden first. Ren prefers Bitwarden over any other store for new passwords.

## Troubleshooting (all verified 2026-11-24)

- `bw unlock` / `bw sync` exit 0 with zero output: that is the 2026.11.0 silent-failure mode. Downgrade to 2025.12.0 to see the real error (e.g. `Failed to decrypt user key with master key` means the password does not match the account's current user key — check you are logging in to the right account with the right password; a `bw logout` + fresh `bw login --passwordenv` fixed it once, and switching to Kit's own account fixed it for good).
- `bw login --passwordfile` silently does nothing (rc 0, no output, still logged out). Never use it for login; `--passwordfile` is only for unlock. Log in with `--passwordenv`.
- `bw sync` failing with `FetchError: ... /api/accounts/revision-date ... socket hang up` or `Client network socket disconnected before secure TLS connection was established`: transient, retry. Verify the route first with `curl --cacert <cert> https://<server>/alive` (expect 200) and `/api/accounts/revision-date` (expect 401 without auth).
- `bw sync` succeeding but `lastSync` in `bw status` not moving: the server's revision date is unchanged, so sync is a no-op. That is normal, not a failure. `lastSync` is the check for whether a sync actually pulled data.
- `bw list items` showing fewer items than the web vault: the CLI reads the local cache. Check `lastSync` first, then `sync` again. The server `/api/sync` response is the source of truth for totals (verified 2026-11-24: the server sync showed far more ciphers than the stale CLI cache).
- Do not assume collection contents stay put: the owner can move items between collections (2026-11-24 the org's items moved out of 默认集合 into `web`/`ssh`). Always list collections and filter by the current collection id.

## Ren's setup

- Ren's Vaultwarden runs on lucas in Docker at `https://100.89.77.121:8080` with data in `/vol2/1000/app/Bitwarden`.

- The server uses a self signed certificate at `~/workspace/vaultwarden-lucas-cert.pem`, valid 2026-11-23 to 2036-11-20. Trust it with `NODE_EXTRA_CA_CERTS` on every bw call.

- The CLI in the sandbox is already pointed at that server and logged in as Kit's own account `kit@<your-domain>` (registered 2026-11-24, confirmed member of organization `lucas`, status 2). The organization holds its items across collections `mail`, `ssh`, `web`, 默认集合 (counts change as the owner reorganizes). The owner's own account is no longer used by the CLI; its items are visible to Kit only through the shared organization.

- Registration on the server was recorded closed (SIGNUPS_ALLOWED=false) on 2026-11-23, but the register page was open on 2026-11-24 when Kit registered. Check the current state before assuming it is closed.

## Available connectors

- [Vaultwarden](~/workspace/custom-connectors/custom.vaultwarden/CONNECTOR.md)

- Use `muse.connector_search` to find other connectors and `muse.skill_search` to find related skills.

- If nothing here fits, look on the web for a maintained API or MCP server and set it up with [Custom Connectors and MCPs](/opt/muse/skills/custom-connector-setup/SKILL.md), or build a custom connector.

## Websites

- [Vaultwarden web vault](https://100.89.77.121:8080/) for creating the account, managing items and folders, and making an API key. The page uses a self signed certificate, so the browser shows a warning before it opens.

- [Bitwarden CLI docs](https://bitwarden.com/help/cli/) for the full command reference. Carry the exact command and its flags into the work and verify the result there.

## Alternatives for better results

- When the CLI cannot reach the server, use the web vault or a desktop or mobile Bitwarden client with the same server address. Those clients are not bound by the sandbox proxy.

- When the web vault is unreachable from a browser, open an SSH tunnel to lucas and use `https://localhost:8080` as the address.
