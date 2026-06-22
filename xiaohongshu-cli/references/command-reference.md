# Command Reference

This is the operational reference for `xiaohongshu-cli` 0.6.4. Commands use JSON
output so their results can be inspected safely and consistently.

```bash
xhs <command> --json
```

Successful results use an envelope with `ok: true` and a `.data` payload. Failures
use `ok: false` and an `.error` object. Inspect only the fields needed for the task;
do not expose cookies, `xsec_token` values, or unrelated account data.

## 1. Authentication decision tree

### Check for an existing saved session without touching browsers

```bash
test -f ~/.xiaohongshu-cli/cookies.json && echo "SAVED_SESSION" || echo "LOGIN_NEEDED"
```

If `SAVED_SESSION` is returned, verify it:

```bash
xhs status --json
```

If the saved session has expired and this causes a browser refresh prompt, stop and
return to the explicit login choices below. Do not allow automatic browser scanning.

### Login from one user-selected browser

The browser must already be logged in to Xiaohongshu. Specify it directly:

```bash
xhs login --cookie-source edge --json
```

Other supported examples include `chrome`, `safari`, `arc`, `brave`, and `firefox`.
Do not use `auto` unless the user specifically accepts trying all supported browsers.

On macOS, the selected Chromium browser can ask to unlock its `Safe Storage` Keychain
item. Explain that this permits the CLI to copy the Xiaohongshu session from that
specific browser. The user should approve once only if they explicitly selected this
method. Never ask for their password or cookie values.

### QR-code login

```bash
xhs login --qrcode --json
```

The browser-assisted QR flow can download a Camoufox browser runtime on first use
(about 300 MB). State that cost and obtain the user's approval before starting it.
It avoids reading cookies from an installed browser.

After either login method, verify with `xhs status --json` or `xhs whoami --json`.

### Account commands

| Command | Purpose | Write effect |
|---|---|---|
| `xhs status --json` | Verify saved session and summarize login state | None |
| `xhs whoami --json` | Show the current account profile | None |
| `xhs logout --json` | Remove saved `cookies.json` | Local account-state deletion |

`logout` needs confirmation because it changes local authentication state.

## 2. Discover and read notes

Run these calls serially. A full Xiaohongshu note URL is preferred over a bare ID
because it carries its note access context.

| Task | Command |
|---|---|
| Search notes | `xhs search "<keyword>" --json` |
| Search sorted or filtered notes | `xhs search "<keyword>" --sort popular --type video --json` |
| Read a note | `xhs read "<note-id-or-full-url>" --json` |
| Read first-level comments | `xhs comments "<note-id-or-full-url>" --json` |
| Read all comment pages | `xhs comments "<note-id-or-full-url>" --all --json` |
| Read replies to one comment | `xhs sub-comments "<note-id>" "<comment-id>" --json` |
| Browse recommendations | `xhs feed --json` |
| Browse a trend category | `xhs hot -c food --json` |
| Search topics / hashtags | `xhs topics "<keyword>" --json` |
| Search users | `xhs search-user "<keyword>" --json` |

Hot categories are `fashion`, `food`, `cosmetics`, `movie`, `career`, `love`,
`home`, `gaming`, `travel`, and `fitness`.

### Note references and cached short indexes

Listing commands such as `search`, `feed`, `hot`, `user-posts`, `favorites`, and
`my-notes` save the latest list locally. This enables references such as:

```bash
xhs read 1 --json
xhs comments 1 --json
```

The index is transient and changes whenever another listing runs. Prefer the full URL
or note ID when correctness matters. The CLI caches note access contexts for about a
day, but stale tokens can fail; use the full URL again rather than retrying blindly.

### Reading one of the user's own notes

Own notes have a special path. First list them:

```bash
xhs my-notes --json
```

For the chosen item, use its returned `id` and matching `xsec_token`:

```bash
xhs read "<id>" --xsec-token "<matching-token>" --json
```

The CLI currently does not reliably carry the own-note token into `xhs read 1`; that
shortcut can return empty data. Treat the token as private access context and never
repeat it in output.

## 3. Profiles, own content, saved content, and notifications

| Task | Command |
|---|---|
| View a profile | `xhs user "<user-id>" --json` |
| List a user's posts | `xhs user-posts "<user-id>" --cursor "<cursor>" --json` |
| List own published posts | `xhs my-notes --page 0 --json` |
| List own favorites | `xhs favorites --json` |
| List another user's favorites when available | `xhs favorites "<user-id>" --json` |
| Show unread counts | `xhs unread --json` |
| Show notifications | `xhs notifications --type likes --json` |

Notification types depend on the server response; use `xhs notifications --help`
before assuming a type beyond those locally advertised, such as `likes` or `mentions`.

## 4. Account-changing commands

Every command in this section requires immediate explicit confirmation. Before the
command, display the exact note or user target and, for comments, replies, and posts,
the final text. For irreversible actions, call out that they are irreversible.

| Action | Command |
|---|---|
| Like a note | `xhs like "<note-id-or-url>" --json` |
| Remove a like | `xhs like "<note-id-or-url>" --undo --json` |
| Favorite a note | `xhs favorite "<note-id-or-url>" --json` |
| Remove a favorite | `xhs unfavorite "<note-id-or-url>" --json` |
| Comment | `xhs comment "<note-id-or-url>" -c "<final-text>" --json` |
| Reply | `xhs reply "<note-id-or-url>" --comment-id "<comment-id>" -c "<final-text>" --json` |
| Delete own comment | `xhs delete-comment "<note-id>" "<comment-id>" -y --json` |
| Follow user | `xhs follow "<user-id>" --json` |
| Unfollow user | `xhs unfollow "<user-id>" --json` |
| Delete own note | `xhs delete "<note-id-or-url>" -y --json` |

The public delete endpoint is marked experimental by the CLI. A failed delete must
be reported as failed; do not retry it or infer that a note was removed.

## 5. Publish a prepared image note

This CLI does not generate images. Require a validated `xhs-note-creator` draft or
user-supplied local image files first. Check all of the following with the user:

- final title and body;
- exact image paths and order, with 1–9 images total;
- approved topics, if any;
- private or public visibility.

Publish privately unless the user explicitly requests a public post:

```bash
xhs post \
  --title "<final-title>" \
  --body "<final-body>" \
  --images "<cover.png>" \
  --images "<card-01.png>" \
  --private \
  --json
```

Add one approved `--topic "<topic>"` flag per topic. Hashtags in the body may also
be resolved by the CLI; keep the combined topic set concise. The command uploads each
given image, then creates an image note. There is no CLI dry-run mode, so the final
confirmation is the preflight.

Use public visibility only after explicit approval by omitting `--private`. After a
successful response, summarize the publication result without exposing request
tokens, cookies, or raw payloads.

## 6. Failure handling and rate limits

| Error condition | Required response |
|---|---|
| `not_authenticated` or expired session | Stop; ask the user to choose an explicit login method |
| `verification_required` | Stop; ask the user to complete the browser/app verification |
| `ip_blocked` | Stop; do not retry or increase request volume |
| `signature_error` or `api_error` | Report the failure and local CLI version; do not invent a workaround |
| `unsupported_operation` | Report that the endpoint is unavailable in this CLI version |

The client adds request jitter, but that is not permission to batch aggressively.
Do not run parallel requests. For a large research task, narrow the request, process
one page at a time, and stop immediately when the platform asks for verification.

## 7. Local state and cleanup

The CLI keeps account state in `~/.xiaohongshu-cli/`:

| File | Purpose |
|---|---|
| `cookies.json` | Saved login cookies and timestamp; refreshed after roughly seven days |
| `token_cache.json` | Note access contexts; retained for roughly one day, capped in size |
| `index_cache.json` | Last ordered note list for numeric references |
| `search_sessions.json` | Search session IDs; short-lived, about ten minutes |

`xhs logout` removes only `cookies.json`. Removing the directory clears all CLI state,
including indexes and tokens; treat that as a user-approved local deletion, not a
routine recovery action.

## 8. Common safe workflows

### Research a note and its discussion

```bash
xhs search "<topic>" --json
xhs read "<full-note-url>" --json
xhs comments "<full-note-url>" --all --json
```

### Review a prepared post before publication

```bash
python xhs-note-creator/scripts/validate_draft.py "xhs-note-creator/drafts/<slug>"
```

Then show the draft's final title, body, output image list, topics, and privacy mode.
Only after explicit approval, run the single `xhs post` command.
