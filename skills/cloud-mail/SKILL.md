# Use ren's Cloud Mail API (mail.520141025.xyz)

Ren's Cloud Mail is the open-source [maillab/cloud-mail](https://github.com/maillab/cloud-mail)
(Cloudflare Workers + D1/R2, one domain, many mailboxes), deployed at
`https://mail.520141025.xyz`. Use its REST API to read mail, list and manage
mailbox addresses, and (when sending is enabled) send mail. Do not drive the
web UI for these jobs; the API is the reliable path.

Official API doc: [api-doc.md](https://github.com/maillab/cloud-mail-docs/blob/HEAD/docs/en/api/api-doc.md)
(the `skymail.ink` host in its examples is the demo — use `mail.520141025.xyz`).

## Credentials — from bw, never hardcoded

- The Cloud Mail account lives in Vaultwarden, org `lucas`, collection `mail`.
  The verification account is the item **`cloud-mail-ikcuhjve`**
  (`ikcuhjve@520141025.xyz`, a one-time mailbox Kit created 2026-11-13 for a
  Muse registration attempt; it is **not** the admin account).
  The admin account is `lucas@520141025.xyz`; its password is not in bw —
  ren types it himself if an admin job ever needs it.
- The helper `bin/cloud-mail.py` reads the account from bw itself
  (`bw-auto.sh get username/password <item>`), so no password ever passes
  through chat, a file, or a command line. Override the item with
  `--item <name>` or `CLOUD_MAIL_BW_ITEM`, or set `CLOUD_MAIL_EMAIL` /
  `CLOUD_MAIL_PASSWORD` in your own terminal.
- To use a different mailbox, add it to bw first: create a login item in
  the org `lucas` mail collection (find the collection id with
  `bw-auto.sh list collections`), username = full `@520141025.xyz` address,
  URI `https://mail.520141025.xyz/`. See the bitwarden skill for the
  `bw encode` / `bw create item` flow.
- Never print a password or a token. The helper prints only API responses
  with the token stripped.

## Auth — and the two quirks that will bite you

- `POST /api/login` with `{"email", "password"}` returns
  `{"code": 200, "data": {"token": "..."}}`.
- Every other call sends the token **raw** in the `Authorization` header.
  Do **not** add a `Bearer ` prefix.
- **Quirk 1 — flaky token check (verified 2026-11-24):** the same valid
  token returns 200 or 401 (`身份认证失效,请重新登录`) at random on
  repeated calls, on every endpoint. The failure rate varies by time:
  one window had `loginUserInfo` 401 four times in a row and send 401
  three of four times, while minutes earlier the same calls passed.
  Never treat 401s as a bad password. Retry the call, re-logging in for
  a fresh token; the helper does up to 6 attempts. If that still fails,
  wait a few minutes and try again — the service recovers on its own.
- **Quirk 2 — Cloudflare blocks the default Python User-Agent**, and the
  connection sometimes drops (`RemoteDisconnected`). Always send a browser
  User-Agent and retry transport errors. The helper does both.
- Responses are always `{"code", "message", "data"}`; `code` 200 is success.
  Times (`createTime`) are UTC.

## Helper

`bin/cloud-mail.py` (stdlib only) wraps the retry logic. It exits 0 only
on `code` 200.

```sh
bin/cloud-mail.py whoami                                   # GET /api/my/loginUserInfo
bin/cloud-mail.py accounts                                 # GET /api/account/list
bin/cloud-mail.py emails --account-id 102 --size 10        # GET /api/email/list (type 0 received, 1 sent)
bin/cloud-mail.py emails --account-id 102 --size 5 --full 1
bin/cloud-mail.py add-account newname@520141025.xyz        # POST /api/account/add
bin/cloud-mail.py delete-account 135                        # DELETE /api/account/delete
bin/cloud-mail.py send --account-id 102 --to a@x.com --subject S --content '<div>..</div>'
bin/cloud-mail.py delete-email 238                         # DELETE /api/email/delete
bin/cloud-mail.py admin-users                              # GET /api/user/list (admin only)
bin/cloud-mail.py admin-add-user new@520141025.xyz         # POST /api/user/add (admin only, password prompted)
bin/cloud-mail.py regkeys                                  # GET /api/regKey/list (admin only)
```

## Endpoints

| Call | Method | Notes |
| --- | --- | --- |
| Sign in | `POST /api/login` | `email`, `password` |
| Current user | `GET /api/my/loginUserInfo` | Role, `permKeys`, current address |
| Email list | `GET /api/email/list?accountId=&size=&type=&full=` | Cursor `emailId`, max size 50, `full=1` returns body + attachments |
| Send email | `POST /api/email/send` | `accountId`, `receiveEmail[]`, `subject`, `content` (HTML), `text`, `name`, `sendType` (`reply`/`forward`), `emailId`, `attachments[]` (Base64, max 10) |
| Delete email | `DELETE /api/email/delete?emailIds=1,2` | Marks deleted by default |
| Address list | `GET /api/account/list?size=` | Max 30 |
| Add address | `POST /api/account/add` | `email` must be a configured domain; `token` (captcha) only if add-verification is on |
| Delete address | `DELETE /api/account/delete?accountId=` | Cannot delete the sign-in primary address |
| User list | `GET /api/user/list?num=&size=&email=` | Admin only |
| Add user | `POST /api/user/add` | Admin only, password min 6 chars |
| Set user status | `PUT /api/user/setStatus` | Admin only, `userId`, `status` 0/1 |
| Delete user | `DELETE /api/user/delete?userIds=` | Admin only, permanent |
| All mail | `GET /api/allEmail/list?type=&size=` | Admin only; `type` all/receive/send/delete/noone |
| Invite codes | `GET /api/regKey/list`, `POST /api/regKey/add`, `GET /api/regKey/history?regKeyId=`, `DELETE /api/regKey/delete?regKeyIds=` | Admin only |

## Verified 2026-11-24 (account ikcuhjve@520141025.xyz, userId 66, accountId 102, role 普通用户)

- Login, `loginUserInfo`, `account/list`, `email/list` all work (with the
  retry loop; a single call may 401). Inbox had 1 mail: Meta's verification
  mail from 2026-11-13.
- `account/add` works: created `cmtestsmo9on@520141025.xyz` (accountId 135),
  confirmed in `account/list`, then deleted; the delete endpoint itself is
  flaky (mostly 401, sometimes 500 `Cannot read properties of undefined
  (reading 'email')`) — always confirm with `account/list` afterwards.
- **Sending is disabled on ren's instance:** `email/send` returns
  `403 邮件发送功能已停用` for this account and two other @520141025.xyz /
  @dissipator.eu.org / @6a105.ccwu.cc mailboxes (confirmed again in a
  later test window: 1 of 4 send attempts reached the 403, the rest 401'd
  on the token check). Receiving still works. Do not keep retrying send;
  re-enable sending in the admin settings first, then re-test. The helper
  prints that hint on a 403.
- Available domains for new addresses (from the role record):
  `520141025.xyz`, `6a105.ccwu.cc`, `dissipator.eu.org`, `lucas.ccwu.cc`,
  `6a105.cf` (full list in `loginUserInfo` → `role.availDomain`).

## Safety

- Sending is a real outbound email: confirm recipient, subject, and body
  with the user first, and send from the address they chose.
- Deleting an email or an address is destructive: confirm the exact id
  first, and re-check with a list call after.
- Admin endpoints (`/api/user/*`, `/api/allEmail/*`, `/api/regKey/*`) need
  the admin account or a role with that permission; a normal user gets a
  permission error, not a silent success. Do not use the admin account
  unless the task genuinely needs admin.
- The verification account `ikcuhjve@` is a shared org item: any agent in
  org `lucas` can read it. Use it for API checks and throwaway addresses;
  for anything that should stay private, use a mailbox only you hold.

## Available connectors

- [Vaultwarden](~/workspace/custom-connectors/custom.vaultwarden/CONNECTOR.md)
  — where the Cloud Mail account password lives.

- Use `muse.connector_search` to find other connectors and
  `muse.skill_search` to find related skills.

- If nothing here fits, look on the web for a maintained API or MCP server
  and set it up with [Custom Connectors and MCPs](/opt/muse/skills/custom-connector-setup/SKILL.md),
  or build a custom connector.

## Websites

- [Cloud Mail](https://mail.520141025.xyz/) — webmail login.
- [API doc](https://github.com/maillab/cloud-mail-docs/blob/HEAD/docs/en/api/api-doc.md)
  — full endpoint reference for maillab/cloud-mail.
- [Cloud Mail repo](https://github.com/maillab/cloud-mail) — upstream source.
