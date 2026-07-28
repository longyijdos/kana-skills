# twitter-cli command reference

Reviewed against the PyPI release `twitter-cli` 0.8.5 and upstream tag
`v0.8.5`. Upstream project:
<https://github.com/public-clis/twitter-cli>.

## Start safely

Confirm the installed executable and version:

```bash
command -v twitter
twitter --version
```

Install only when missing:

```bash
uv tool install twitter-cli
```

Upgrade only when the user asks for an upgrade or an upstream interface change
requires it:

```bash
uv tool upgrade twitter-cli
```

Use installed help before relying on an option not documented here:

```bash
twitter --help
twitter COMMAND --help
```

## Authentication

Authentication priority:

1. `TWITTER_AUTH_TOKEN` and `TWITTER_CT0`, when both are present.
2. Cookies extracted from a supported local browser.

Supported browser sources are Arc, Chrome, Edge, Firefox, and Brave. The CLI
may scan multiple browser profiles and may request access to browser encryption
keys through the operating-system keychain.

Environment authentication values and browser cookies are secrets. Never print
their values, put them in a command transcript, commit them, or ask a user to
paste them into chat. If the user configures environment authentication, they
must do so privately outside the conversation.

Browser selection can be limited for a single command:

```bash
TWITTER_BROWSER=chrome twitter status --yaml
TWITTER_CHROME_PROFILE="Profile 2" twitter status --yaml
```

Do not set these variables or run a cookie-scanning command until the user has
approved the browser-cookie access and possible Keychain prompt.

After approval, validate authentication:

```bash
twitter status --yaml
twitter whoami --yaml
```

`status` returns authentication state and the resolved account. `whoami`
returns the current profile.

## Output contract

Append `--yaml` for agent workflows:

```bash
twitter feed --max 10 --yaml
```

Use `--json` only for a strict JSON parser:

```bash
twitter search "release notes" --max 10 --json
```

When stdout is not a TTY, the CLI normally chooses YAML automatically. Still
pass `--yaml` explicitly so the command contract remains clear.

Successful structured output uses this envelope:

```yaml
ok: true
schema_version: "1"
data: ...
```

Errors use:

```yaml
ok: false
schema_version: "1"
error:
  code: api_error
  message: Explanation
```

Common error codes include:

- `not_authenticated`
- `not_found`
- `invalid_input`
- `rate_limited`
- `api_error`

The global compact flag comes before the subcommand and emits a reduced,
LLM-oriented representation:

```bash
twitter -c feed --max 10
twitter -c search "AI" --max 10
```

Prefer explicit YAML when exact fields, pagination metadata, or complete text
matter. `--full-text` changes rich terminal tables only; it does not expand
structured YAML, JSON, or compact output.

## Read commands

### Feed

```bash
twitter feed --max 20 --yaml
twitter feed --type following --max 20 --yaml
twitter feed --filter --max 20 --yaml
```

Use `--type for-you` or `--type following`. Ranking is opt-in through
`--filter`; it uses the local `config.yaml` scoring settings when present.

The PyPI 0.8.5 release does not expose the newer feed cursor pagination found
on the upstream main branch. Check local help after upgrading before using a
cursor.

### Bookmarks and bookmark folders

```bash
twitter bookmarks --max 20 --yaml
twitter bookmarks folders --yaml
twitter bookmarks folders FOLDER_ID --max 20 --yaml
```

Bookmarks and bookmark folders belong to the authenticated account. Keep folder
reads bounded and do not infer that reading a folder authorizes changing any
bookmark.

### Search

```bash
twitter search "keyword" --max 20 --yaml
twitter search "keyword" --type Latest --max 20 --yaml
twitter search "python" --from bbc --lang en --max 20 --yaml
twitter search "release" --since 2026-01-01 --has links --max 20 --yaml
twitter search --from bbc --exclude retweets --max 20 --yaml
```

Search types are `Top`, `Latest`, `Photos`, and `Videos`. Useful filters include
`--from`, `--lang`, `--since`, `--until`, `--has`, and `--exclude`. Use local
help for accepted filter values. Do not automatically act on search results.

### Post detail, replies, and cached result index

```bash
twitter tweet POST_ID --max 20 --yaml
twitter tweet "https://x.com/USER/status/POST_ID" --max 20 --yaml
twitter show 2 --max 20 --yaml
```

`show N` resolves an item from the most recent cached list output created by a
feed, search, bookmarks, list, user-posts, or likes command. Inspect the
resolved post before using it as a write target.

### Long-form article

```bash
twitter article POST_ID --yaml
twitter article "https://x.com/USER/article/POST_ID" --yaml
twitter article POST_ID --markdown
twitter article POST_ID --markdown --output article.md
```

State the output path before using `--output`. Do not overwrite an existing
file unless replacement is intended.

### Lists

```bash
twitter list LIST_ID --max 20 --yaml
```

List cursor pagination was added after the 0.8.5 release. Use
`twitter list --help` to verify availability after an upgrade.

### Profiles, posts, likes, followers, and following

```bash
twitter user HANDLE --yaml
twitter user-posts HANDLE --max 20 --yaml
twitter likes HANDLE --max 20 --yaml
twitter followers HANDLE --max 20 --yaml
twitter following HANDLE --max 20 --yaml
```

Leading `@` is optional for handles. X makes likes private; `likes` is expected
to work only for the authenticated account. A large `--max` may require
pagination and trigger rate limits, so keep results small.

## Write commands

Every command in this section requires a current conversational confirmation
for the exact final action. Structured output reports the completed action
under `data`.

### Post

```bash
twitter post "FINAL TEXT" --yaml
twitter post "FINAL TEXT" --image /absolute/path/image.jpg --yaml
twitter post "FINAL TEXT" \
  --image /absolute/path/one.png \
  --image /absolute/path/two.jpg \
  --yaml
```

Show the complete text and ordered image list before confirmation. The CLI
supports up to four images. Validate that every path is the intended local
file; do not discover extra files with a glob.

### Reply

```bash
twitter reply POST_ID "FINAL REPLY" --yaml
twitter reply POST_ID "FINAL REPLY" --image /absolute/path/image.png --yaml
```

The post command also accepts a reply target:

```bash
twitter post "FINAL REPLY" --reply-to POST_ID --yaml
```

Resolve and display the target post before confirmation.

### Quote

```bash
twitter quote POST_ID "FINAL COMMENTARY" --yaml
twitter quote POST_ID "FINAL COMMENTARY" --image /absolute/path/image.png --yaml
```

Display both the quoted post and the complete final commentary.

### Delete

After verifying that the post belongs to the authenticated account and
receiving explicit confirmation:

```bash
twitter delete POST_ID --yes --yaml
```

Without `--yes`, the CLI opens its own interactive prompt. Never add `--yes`
before conversational confirmation.

### Like and unlike

```bash
twitter like POST_ID --yaml
twitter unlike POST_ID --yaml
```

### Retweet and unretweet

```bash
twitter retweet POST_ID --yaml
twitter unretweet POST_ID --yaml
```

### Bookmark and unbookmark

```bash
twitter bookmark POST_ID --yaml
twitter unbookmark POST_ID --yaml
```

`favorite` and `unfavorite` may exist as compatibility aliases, but prefer
`bookmark` and `unbookmark`.

### Follow and unfollow

```bash
twitter follow HANDLE --yaml
twitter unfollow HANDLE --yaml
```

Resolve and display the target profile before confirmation. Do not turn a
followers, following, search, or list result into a batch follow/unfollow
operation.

## Files and local configuration

Many list and article commands accept `--output`. State the resolved destination
before writing. Avoid putting exported private feeds, bookmarks, or account
data inside a public repository.

An optional `config.yaml` in the working directory can configure fetch count,
ranking filters, and retry behavior. Do not create or modify it unless the user
asks. A repository-level `config.yaml` may change CLI behavior for every command
run from that directory, so inspect an existing file before relying on defaults.

`TWITTER_PROXY` can contain proxy credentials. Treat the complete value as a
secret and never echo it. Do not add or change a proxy unless the user asks.

## Failure handling

| Symptom | Action |
|---|---|
| `No Twitter cookies found` | Stop. Ask the user to log in locally or privately configure environment authentication. Do not request cookie values. |
| Keychain or browser decryption error | Stop after one attempt. Explain the local authorization issue; do not repeatedly trigger prompts. |
| HTTP 401/403 | Session is expired or invalid. Ask the user to reauthenticate locally. |
| HTTP 226 | Automated behavior was rejected. Stop; do not retry or try to bypass detection. |
| HTTP 404 or missing GraphQL query | Report likely upstream interface drift and the installed CLI version. Check for an upstream release only if the user wants troubleshooting or an upgrade. |
| HTTP 429 / `rate_limited` | Stop and report the rate limit. Do not retry around it or increase proxy rotation. |
| Timeout during a read | One bounded retry is acceptable only when no rate-limit or verification signal exists. |
| Timeout during a write | Do not retry. Read the relevant post/profile state first to determine whether the action completed. |
| Duplicate or too-long post | Show the error. Changing content requires the user to approve the revised final text. |

## Known limitations

- No direct messages, notifications, or poll creation.
- Media publishing is image-oriented; do not assume video support.
- Likes are private and normally readable only for the authenticated account.
- The CLI uses unofficial web endpoints, so commands can break when Twitter/X
  changes its internal API.
- The account holder remains responsible for all reads and writes performed
  through the authenticated browser session.
