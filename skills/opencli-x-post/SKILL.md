---
name: opencli-x-post
description: Post and reply on X (Twitter) through the logged-in Chrome via OpenCLI browser commands. Covers single posts, threads, and replies, with connection recovery for the Browser Bridge extension.
allowed-tools: Bash(opencli:*), Read, Edit, Write
---

# Post and reply on X with OpenCLI

Drive the user's logged-in Chrome to post and reply on X. All page commands
need `--session <name>`; reuse one session name for the whole task. Different
sessions isolate page work. `--profile <name>` selects a Chrome profile when
more than one is connected.

Verified against: OpenCLI CLI 2.0.3 (`npm install -g @jackwener/opencli`,
Node v22), Google Chrome on an Instabox box with the Browser Bridge
extension, X logged in as @MingluL19015.

## Install and connect

```sh
node --version  # >= 20.18.1
npm install -g @jackwener/opencli
opencli doctor
```

OpenCLI reaches Chrome through the OpenCLI Browser Bridge extension plus a
local daemon. The daemon listens on `127.0.0.1:19825`; the extension connects
to it over WebSocket at `ws://127.0.0.1:19825/ext`. `opencli doctor` reports
`extensionConnected` and, once connected, one profile (`contextId`).

If `doctor` shows `extensionConnected: false`, the extension's service
worker is asleep. Wake it by opening the extension popup page in Chrome:

```
chrome-extension://ildkmabpimmkaediidaifkhjpohdnifk/popup.html
```

or restart the daemon and check again:

```sh
opencli daemon restart
opencli doctor
```

Discover commands with `opencli list <query>`; read exact arguments with
`opencli browser <command> --help -f json`. Default output is one JSON
value: `{ "ok": true, "data": ... }`. Failures return
`{ "ok": false, "error": { "code": "...", "message": "...", "hint": "..." } }`
with a nonzero exit code. When `error.outcome` is `unknown`, inspect the
affected state before retrying a write.

## Single post

```sh
opencli browser open https://x.com/compose/post --session xpost
opencli browser find --testid tweetTextarea_0 --session xpost
```

The composer is a contenteditable `div`: `role=textbox`,
`aria-label="Post text"`, `data-testid="tweetTextarea_0"`. The page can
carry two `tweetTextarea_0` elements (the home timeline's inline composer
and the compose modal's); the modal's is the later one, with the higher ref
number. Target it by ref.

```sh
opencli browser type <ref> "<text>" --session xpost
opencli browser get text <ref> --session xpost
```

`type` clicks the box, then types. Newlines in the text become line breaks
in the post, not a submit. Emoji and CJK text type as-is. Always verify
with `get text` before publishing: the returned value must match the
intended text exactly.

```sh
opencli browser click --testid tweetButton --session xpost
```

That clicks the Post button (`data-testid="tweetButton"`). Confirm the post
went out by opening the profile page or the post URL afterwards.

Length: a free X account allows 280 characters per post, and every URL
counts as 23 characters regardless of its real length. Split longer content
into several posts (see below).

## Threads (multiple posts)

Preferred method: post the first item, then reply to it (see Reply). A
reply to your own post reads as a thread, and each step is verified
independently.

Alternative: the composer's "+" button. It is an `<a>` element,
`data-testid="addButton"`, `aria-label="Add post"`, and only appears once
the composer has content. Clicking it adds a second composer
(`tweetTextarea_1`); type the second post there, then click Post all.

```sh
opencli browser click --testid addButton --session xpost
opencli browser find --testid tweetTextarea_1 --session xpost
```

Caution: in a live test (2026-11-20), `opencli browser click --testid
addButton` reported success but no second composer appeared and the draft
was cleared. Treat "+" as a fallback: after clicking it, re-run `find` for
`tweetTextarea_1` and re-check the first draft with `get text` before
typing anything. If the draft is gone, retype it.

## Reply

```sh
opencli browser open <post URL> --session xpost
opencli browser click --testid reply --session xpost
opencli browser find --testid tweetTextarea_0 --session xpost
opencli browser type <ref> "<text>" --session xpost
opencli browser get text <ref> --session xpost
opencli browser click --testid tweetButton --session xpost
```

Open the post to reply to, click its reply button
(`data-testid="reply"`), and the reply composer opens. It is the same
`tweetTextarea_0` textbox: type, verify with `get text`, then click Post.
Replying to your own just-posted post chains posts into a thread.

## General rules

- Confirm page state after every key step with `state`, `find`, or
  `get text` before continuing. Never assume a ref number is still valid:
  DOM changes renumber refs, so re-run `find` before each action.
- Posting is a public action. Show the user the full text for approval
  first, or post only text the user has already confirmed. Do not reword
  on your own.
- On connection trouble, run `opencli doctor` (see Install and connect).
  End the task with:

```sh
opencli browser close --session xpost
```
