# Use Bitwarden CLI (bw)

## Install bw

- Install the CLI with npm into the home directory, so it survives sandbox rebuilds.

- Run `npm install -g @bitwarden/cli --prefix ~/.npm-global` and link it with `ln -sf ~/.npm-global/bin/bw ~/.local/bin/bw`.

- Check the install with `bw --version`. Version 2026.11.0 is the one verified on 2026-11-23.

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

- Never put the master password in a command argument, an environment variable, a file, a log or a chat message. Let the user type it at the prompt, or use `--passwordenv` with a variable the user set, or `--passwordfile` with a 600 file the user wrote.

- Ask the user for the master password only when the task genuinely needs a login. Offer the Secure Vault card first, and use a password the user sends in chat only for that one login and never store it.

- Unlock the vault with `bw unlock`. It prints a session key, so export it as `BW_SESSION` for later commands in the same shell.

- An unlock invalidates earlier session keys. Run `bw lock` when the work is done, and run `bw logout` to end the login entirely.

- Check the state with `bw login --check` and `bw unlock --check` before you assume a command will work.

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

## Ren's setup

- Ren's Vaultwarden runs on lucas in Docker at `https://100.89.77.121:8080` with data in `/vol2/1000/app/Bitwarden`.

- The server uses a self signed certificate at `~/workspace/vaultwarden-lucas-cert.pem`, valid 2026-11-23 to 2036-11-20. Trust it with `NODE_EXTRA_CA_CERTS` on every bw call.

- The CLI in the sandbox is already pointed at that server. The first login still needs the user's master password.

- Registration on the server is closed. New accounts are made by the user in the web vault.

## Available connectors

- Use `muse.connector_search` to find other connectors and `muse.skill_search` to find related skills.

- If nothing here fits, look on the web for a maintained API or MCP server and set it up with [Custom Connectors and MCPs](/opt/muse/skills/custom-connector-setup/SKILL.md), or build a custom connector.

## Websites

- [Vaultwarden web vault](https://100.89.77.121:8080/) for creating the account, managing items and folders, and making an API key. The page uses a self signed certificate, so the browser shows a warning before it opens.

- [Bitwarden CLI docs](https://bitwarden.com/help/cli/) for the full command reference. Carry the exact command and its flags into the work and verify the result there.

## Alternatives for better results

- When the CLI cannot reach the server, use the web vault or a desktop or mobile Bitwarden client with the same server address. Those clients are not bound by the sandbox proxy.

- When the web vault is unreachable from a browser, open an SSH tunnel to lucas and use `https://localhost:8080` as the address.
