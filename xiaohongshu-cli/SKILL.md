---
name: xiaohongshu-cli
description: |
  Use this for Xiaohongshu (小红书, XHS, Redbook) operations including searching
  notes, reading note content or comments, browsing users and trends, and managing
  the authenticated account. Requires the local xhs CLI. Obtain explicit user
  confirmation immediately before any write operation: like, favorite, follow,
  comment, reply, post, or delete.
---

# Xiaohongshu CLI

Use the `xhs` command supplied by the `xiaohongshu-cli` package. Prefer its
machine-readable output for all agent work:

```bash
xhs <command> --json
```

## Setup

Install once when the `xhs` command is unavailable:

```bash
uv tool install xiaohongshu-cli
```

The CLI stores its own account state outside the skill and repository:

```text
~/.xiaohongshu-cli/
```

This directory can contain:

- `cookies.json` — copied Xiaohongshu session cookies and a saved timestamp.
- `token_cache.json` — short-lived note access tokens.
- `index_cache.json` — the latest note list for numeric references such as `xhs read 1`.
- `search_sessions.json` — short-lived search session IDs.

Cookie and cache files are private account state. Never request, print, or include
their contents in logs or chat. `xhs logout` removes only `cookies.json`; removing
the whole directory clears all CLI state.

## Authentication

Before any command that talks to Xiaohongshu, check authentication:

```bash
xhs status --json
```

If authentication is unavailable, ask the user to complete one of these local
commands themselves, then re-check status:

```bash
xhs login
xhs login --qrcode
```

`xhs login` reads the locally logged-in browser's Xiaohongshu cookies and saves a
copy in `~/.xiaohongshu-cli/cookies.json`; it does not require pasting a cookie
into chat. `xhs login --qrcode` may require a separately installed Camoufox browser
runtime.

If a command returns `verification_required`, `ip_blocked`, or a session-expiry
error, stop retries and ask the user to complete the browser verification or login.

## Read-only operations

Run these serially. Do not parallelize `xhs` calls or run bulk polling.

| Need | Command |
|---|---|
| Search notes | `xhs search "keyword" --json` |
| Read a note | `xhs read "<note-id-or-url>" --json` |
| Read comments | `xhs comments "<note-id-or-url>" --json` |
| Read all comments | `xhs comments "<note-id-or-url>" --all --json` |
| Browse a user's profile | `xhs user "<user-id>" --json` |
| List a user's notes | `xhs user-posts "<user-id>" --json` |
| Browse recommendations | `xhs feed --json` |
| Browse category trends | `xhs hot -c food --json` |
| Search topics | `xhs topics "keyword" --json` |
| Search users | `xhs search-user "keyword" --json` |
| View own notes | `xhs my-notes --json` |

Available hot categories: `fashion`, `food`, `cosmetics`, `movie`, `career`,
`love`, `home`, `gaming`, `travel`, `fitness`.

For a note URL, pass the full URL unchanged so its access token can be used. Numeric
references such as `xhs read 1` depend on the latest cached list; prefer a note URL
or ID when accuracy matters.

## Write operations

These change the user's Xiaohongshu account or publish content. Immediately before
running a command, show the exact target and final text/options, then obtain the
user's explicit confirmation in the current conversation. Do not treat a general
request as confirmation for a later final payload.

| Action | Command |
|---|---|
| Like / unlike | `xhs like "<note-id-or-url>"` / `xhs like "<...>" --undo` |
| Favorite / remove favorite | `xhs favorite "<note-id-or-url>"` / `xhs unfavorite "<...>"` |
| Comment | `xhs comment "<note-id-or-url>" -c "<final text>"` |
| Reply | `xhs reply "<note-id-or-url>" --comment-id "<id>" -c "<final text>"` |
| Follow / unfollow | `xhs follow "<user-id>"` / `xhs unfollow "<user-id>"` |
| Delete own comment | `xhs delete-comment "<note-id>" "<comment-id>" -y` |

### Posting an image note

Verify the title, body, image paths, topics, and privacy setting with the user.
Publish privately by default:

```bash
xhs post \
  --title "<final title>" \
  --body "<final body>" \
  --images "<image-1>" \
  --images "<image-2>" \
  --private \
  --json
```

Use one `--topic "<topic>"` per topic when the user approved them. Do not publish
publicly unless the user explicitly requests a public note. After success, return
the structured result without exposing cookies or access tokens.

### Deletion

For `xhs delete "<note-id-or-url>" -y`, show the exact note to be deleted and get
explicit confirmation immediately before execution. This action is irreversible.

## Result handling

- Inspect the JSON envelope's `.data` field for successful responses and `.error`
  for failures.
- Summarize only the fields relevant to the user's request; avoid echoing session
  tokens, identifiers not needed for the task, or raw server payloads.
- The platform rate-limits requests. Keep calls serial and stop when verification is
  required instead of trying to bypass it.
