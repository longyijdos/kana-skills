# Command Reference

This is the operational reference for `bilibili-cli` 0.6.2. Query commands use
YAML by default so results are compact and consistently inspectable:

```bash
bili <command> --yaml
```

Successful structured responses use `ok: true`, `schema_version: "1"`, and a
`data` payload. Failures use `ok: false` and an `error` object. Inspect only the
fields necessary for the task. Never expose credentials or unrelated private data.

## 1. Installation and authentication

Install the normal CLI only when `bili` is unavailable:

```bash
uv tool install bilibili-cli
```

The optional `audio` feature needs PyAV and is installed as an extra of the same
package, not as a second CLI:

```bash
uv tool install "bilibili-cli[audio]"
```

If `bili` is already installed without audio support:

```bash
uv tool upgrade "bilibili-cli[audio]"
```

### Check saved login state

Do not trigger a login flow merely to answer a public read request. Check whether a
saved credential exists first:

```bash
test -f ~/.bilibili-cli/credential.json && echo "SAVED_SESSION" || echo "LOGIN_NEEDED"
```

If it exists, verify it:

```bash
bili status --yaml
```

`status` exits 0 when authenticated and 1 when not authenticated. It can make an
account API call; do not loop or retry it on an API or rate-limit failure. A stale
or invalid saved credential can cause the CLI to fall through to automatic browser
cookie scanning; obtain the user's approval before running `status` in that case.

### QR-code login

`bili login` changes local authentication state and displays a QR code. Before
executing it, explain that the user must approve the login by scanning the QR code
with their Bilibili app and get their approval in the current conversation:

```bash
bili login
```

### Automatic browser-cookie fallback

In version 0.6.2, there is no `--cookie-source` option or browser selector. When an
authenticated command needs a credential and has no usable saved credential, the CLI
automatically tries local browsers in this fixed order: Chrome, Firefox, Edge, then
Brave. It saves the first valid Bilibili session it finds to
`~/.bilibili-cli/credential.json`.

It can cause browser database/Keychain access prompts and cannot be constrained to
one browser from the CLI. Therefore, before an authenticated command could trigger
this fallback, explain the exact automatic scan and obtain explicit user approval.
If the user does not approve it, use `bili login` (QR code) instead. Do not request
cookie values, use another person's browser profile, or print cookie-derived data
beyond the requested result. Verify a completed QR login:

```bash
bili status --yaml
```

### Account commands

| Command | Purpose | Write effect |
|---|---|---|
| `bili status --yaml` | Verify saved session | None |
| `bili whoami --yaml` | Show current account profile | None |
| `bili login` | Open QR-code login | Writes saved credential |
| `bili logout` | Delete saved credential | Local account-state deletion |

`login` and `logout` require explicit confirmation. For `logout`, state that it
removes the saved local credential and does not delete the remote Bilibili account.
An authenticated read can itself trigger the automatic browser-cookie fallback
described above, so it also needs approval when no usable saved credential exists.

## 2. Public video, user, search, and discovery reads

Public metadata reads normally work without login. Use a full Bilibili video URL or
a BV ID whenever one is available.

| Task | Command |
|---|---|
| Get video metadata | `bili video "<BV-or-full-url>" --yaml` |
| Get plain subtitles | `bili video "<BV-or-full-url>" --subtitle --yaml` |
| Get timestamped subtitles | `bili video "<BV-or-full-url>" --subtitle-timeline --yaml` |
| Get Bilibili AI summary | `bili video "<BV-or-full-url>" --ai --yaml` |
| Get top comments | `bili video "<BV-or-full-url>" --comments --yaml` |
| Get related videos | `bili video "<BV-or-full-url>" --related --yaml` |
| View an UP 主 profile | `bili user "<UID-or-name>" --yaml` |
| List an UP 主's recent videos | `bili user-videos "<UID-or-name>" --max 5 --yaml` |
| Search users | `bili search "<keyword>" --max 5 --yaml` |
| Search videos | `bili search "<keyword>" --type video --max 5 --yaml` |
| Browse hot videos | `bili hot --max 5 --yaml` |
| Browse ranking | `bili rank --day 3 --max 5 --yaml` |

`bili user <name>` selects the first user-search match. When identity matters,
search first, verify the returned UID and name, then use that UID for subsequent
commands.

### Video analysis order

Use these calls serially and stop as soon as the material answers the request:

```bash
bili video "<BV-or-url>" --subtitle --yaml
bili video "<BV-or-url>" --ai --yaml
bili video "<BV-or-url>" --comments --yaml
```

The second and third calls are fallbacks or supplementary evidence, not defaults.
Subtitles, AI summaries, comments, and related videos can be unavailable or require
login; report the returned warning or error rather than retrying blindly.

## 3. Authenticated reads

The following commands require a valid saved login. Do not run them when the user
only requested public research.

| Task | Command |
|---|---|
| List favorite folders | `bili favorites --yaml` |
| Read a favorite folder | `bili favorites "<folder-id>" --page 1 --yaml` |
| List following | `bili following --page 1 --yaml` |
| Read watch-later | `bili watch-later --yaml` |
| Read history | `bili history --page 1 --max 10 --yaml` |
| Read followed-account dynamics | `bili feed --yaml` |
| Continue a dynamics page | `bili feed --offset "<returned-offset>" --yaml` |
| Read own posted dynamics | `bili my-dynamics --yaml` |

Favorites, history, watch-later, following, feed, and own dynamics can reveal
personal activity. Return only the portion relevant to the request.

## 4. Account-changing commands

Every command in this section requires immediate explicit confirmation. Before
executing, display the exact BV ID, UID, dynamic ID, or full dynamic text and state
the complete effect. Do not rely on the CLI's interactive prompt as a substitute
for confirmation in the conversation.

| Action | Command | Required preflight |
|---|---|---|
| Like | `bili like "<BV-or-url>" --yaml` | Show target BV ID |
| Remove a like | `bili like "<BV-or-url>" --undo --yaml` | Show target BV ID |
| Give coins | `bili coin "<BV-or-url>" --num 1 --yaml` | Show target and `1` or `2` coins |
| Triple-click | `bili triple "<BV-or-url>" --yaml` | Explain: like + coin + favorite |
| Unfollow | `bili unfollow "<UID>" --yes --yaml` | Show target UID and account identity |
| Post text dynamic | `bili dynamic-post "<final-text>" --yaml` | Show exact complete text |
| Delete dynamic | `bili dynamic-delete "<dynamic-id>" --yes --yaml` | Identify item; state irreversible |
| Log out | `bili logout` | State local credential will be deleted |

The credentials used for writes must include `bili_jct`. If write permission is
missing, stop and report it; do not ask the user to expose a token or cookie.

`triple` is a compound operation. It may like, coin, and favorite a video in one
request; treat its three effects as a single higher-impact action. Do not substitute
separate calls or retry individual parts after an ambiguous failure.

## 5. Optional audio extraction

Audio extraction requires the optional package extra described in section 1. It
downloads media and writes files, so first state the BV ID, intended purpose, and
output directory. It does not publish or modify a Bilibili account.

| Task | Command |
|---|---|
| Download and split into 25-second WAV segments | `bili audio "<BV-or-url>"` |
| Set segment duration (5–300 seconds) | `bili audio "<BV-or-url>" --segment 60` |
| Save one complete M4A file | `bili audio "<BV-or-url>" --no-split` |
| Choose output directory | `bili audio "<BV-or-url>" --output "<directory>"` |

The default output is `/tmp/bilibili-cli/<sanitized-video-title>/`. With
`--no-split`, the full M4A is saved to the selected directory. Use a user-approved
directory for artifacts that need to persist. Do not place downloads in
`~/.bilibili-cli/`.

## 6. Failure handling and rate limits

| Error condition | Required response |
|---|---|
| `not_authenticated` | Stop; offer QR-code login or the automatic multi-browser scan, each only with approval |
| `permission_denied` or missing write credential | Stop; report missing permission |
| `rate_limited` or HTTP 412 | Stop; do not retry, parallelize, or increase `--max` |
| `invalid_input` or invalid BV ID | Ask for a corrected BV ID or full URL |
| `network_error` or `upstream_error` | Report the failure and CLI version; do not invent a workaround |
| Partial video output with warnings | Report unavailable fields and use available evidence only |

For a research task spanning many pages, narrow the request, process one page at a
time, and stop if the platform requests verification or signals a rate limit.

## 7. Local state and output contract

The CLI keeps account state under `~/.bilibili-cli/`:

| Path | Purpose |
|---|---|
| `credential.json` | Saved login credential; sensitive |

`bili logout` clears the saved credential. Removing the state directory also clears
it; treat either action as user-approved local deletion, not routine recovery.

Structured output follows this envelope:

```yaml
ok: true
schema_version: "1"
data: ...
```

On failure:

```yaml
ok: false
schema_version: "1"
error:
  code: not_authenticated
  message: ...
```

Use `--json` instead of `--yaml` only where strict JSON is necessary. For any
command or option not covered here, run `bili <command> --help` before assuming it
exists.
