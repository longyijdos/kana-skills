---
name: twitter-cli
description: |
  Use this for Twitter/X account operations: reading feeds, posts, articles,
  bookmarks, lists, profiles, followers, following, likes, and search; and,
  only with explicit confirmation, posting, replying, quoting, deleting,
  liking, bookmarking, retweeting, following, or undoing those actions.
  Requires the local twitter CLI from the twitter-cli package.
---

# Twitter CLI

Use `twitter`, provided by the `twitter-cli` package. This skill manages
Twitter/X operations only.

Before executing any unfamiliar `twitter` command or option, read
[`references/command-reference.md`](references/command-reference.md). It is the
canonical command map, authentication guide, output contract, and failure guide
for this skill. Treat `twitter <command> --help` from the installed version as
authoritative when it differs from the reference.

## Operating rules

1. Prefer machine-readable output: append `--yaml` to reads and writes. Use
   `--json` only when a strict JSON consumer requires it.
2. Run network requests serially. Keep reads narrow, normally with `--max 20`
   or less. Do not bulk scrape, batch interactions, parallelize calls, or retry
   around verification and rate-limit responses.
3. Treat browser cookies, `TWITTER_AUTH_TOKEN`, `TWITTER_CT0`, proxy
   credentials, and browser/keychain data as secrets. Never request, paste,
   print, log, or store their values in chat or repository files.
4. Use a full post URL or exact numeric post ID when available. Resolve and
   inspect ambiguous search or profile results before acting on them.
5. Before every write, show the exact target and final effect, then obtain
   explicit confirmation in the current conversation immediately before
   execution.
6. A confirmation applies only to the displayed action. Changing the post
   text, reply/quote target, image list, account, or action requires a new
   confirmation.
7. Do not automatically turn search, feed, follower, or following results into
   bulk likes, bookmarks, retweets, follows, replies, or posts.
8. After a timeout or lost connection during a write, do not retry blindly:
   inspect the account or target first because the action may have completed.

This CLI uses unofficial Twitter/X web interfaces and may stop working or
trigger account controls when the platform changes. Do not attempt to bypass
rate limits, verification, or account restrictions.

## Setup and authentication

Check the executable before a workflow:

```bash
command -v twitter
twitter --version
```

Install only when `twitter` is unavailable:

```bash
uv tool install twitter-cli
```

The CLI authenticates from `TWITTER_AUTH_TOKEN` plus `TWITTER_CT0` when both
are already present. Otherwise, an authenticated command can scan local
Arc, Chrome, Edge, Firefox, and Brave profiles for Twitter/X cookies. On macOS
this may open a Keychain authorization prompt.

Before allowing an automatic browser scan, tell the user which command will
run, that it may read local browser cookies and trigger a Keychain prompt, and
obtain explicit approval. Never start authentication by silently running
`twitter status`, `twitter whoami`, or another authenticated command.

If the user prefers environment authentication, tell them to configure the two
variables privately in their own environment and return when ready. Do not ask
them to send either value or a complete Cookie header through chat.

Use this only after the authentication method is approved:

```bash
twitter status --yaml
```

If authentication fails, stop and follow the decision table in the command
reference. Do not repeatedly rescan browsers or repeatedly trigger Keychain
prompts.

## Request routing

| User intent | Use |
|---|---|
| Read home or Following feed | `feed` with a small `--max` |
| Search posts | `search`, using the narrowest query and filters |
| Read one post, replies, or a long-form article | `tweet`, `show`, or `article` |
| Inspect a profile or posts | `user` or `user-posts` |
| Inspect own bookmarks or likes | `bookmarks` or `likes` |
| Inspect a list, followers, or following | `list`, `followers`, or `following` |
| Post, reply, quote, or attach images | Preview final text, target, and paths; then confirm |
| Like, bookmark, retweet, follow, or undo one | Resolve the exact target; then confirm |
| Delete a post | Verify ownership and ID; then confirm immediately before deletion |

## Write-operation confirmation

For a post, reply, or quote, show:

- the complete final text;
- the reply or quoted post URL/ID, if any;
- every image path in upload order;
- the resulting public action.

For an interaction, show the exact post URL/ID or `@handle` and whether the
command will add or remove the interaction.

The CLI itself prompts before deletion. After conversational confirmation, use
its non-interactive confirmation flag so an agent command does not block:

```bash
twitter delete POST_ID --yes --yaml
```

Do not add `--yes` before the user has confirmed the exact deletion.

## Version and drift

This reference was written against the PyPI release `twitter-cli` 0.8.5.
Twitter/X web endpoints and GraphQL query identifiers change frequently. Before
using a newly introduced option or after upgrading, run:

```bash
twitter --version
twitter <command> --help
```

If local help differs, use local help as the execution source of truth and
update this skill and its command reference coherently.
