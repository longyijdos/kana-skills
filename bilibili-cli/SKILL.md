---
name: bilibili-cli
description: |
  Use this for Bilibili (哔哩哔哩, B站) account operations: searching and reading
  videos, subtitles, users, rankings, dynamics, favorites, watch-later, and
  history; and, only with explicit confirmation, liking, unliking, giving coins,
  triple-clicking, unfollowing, posting or deleting a dynamic, or logging out.
  Requires the local bili CLI from the bilibili-cli package.
---

# Bilibili CLI

Use `bili`, provided by the `bilibili-cli` package. This skill manages Bilibili
operations only.

Before executing any `bili` command, read
[`references/command-reference.md`](references/command-reference.md). It is the
canonical command map, authentication guide, output contract, and error-handling
guide for this skill.

## Operating rules

1. Prefer machine-readable output: append `--yaml` to query commands. Use `--json`
   only when a later tool or exact JSON processing requires it.
2. Run requests serially. Keep query result sets small with `--max`, `--page`, or
   `--offset`; do not bulk scrape, parallelize calls, or retry around rate limits.
3. Treat `~/.bilibili-cli/credential.json`, browser cookies, `bili_jct`, QR-login
   tokens, and private account data as secrets. Never request or print them.
4. For a read request, use the smallest number of calls that answers the question.
   A BV ID or full video URL is preferred over ambiguous search results.
5. For a write request, first show the exact target and final effect. For a coin,
   show the number of coins; for a dynamic, show its complete final text. Obtain
   explicit confirmation in the current conversation immediately before execution.
6. A request such as “三连这个视频” does not authorize a different video, or a
   changed coin count. A request to publish does not authorize a later changed
   dynamic text.
7. For a video summary, request subtitles first. Use the platform AI summary,
   comments, or audio extraction only when subtitles are unavailable or insufficient.

## Setup and authentication

Install only when `bili` is unavailable:

```bash
uv tool install bilibili-cli
```

Downloading a complete M4A with `bili audio --no-split` works with the base CLI.
WAV splitting requires the same CLI with its `audio` dependency group installed:

```bash
uv tool install "bilibili-cli[audio]"
```

If the ordinary CLI is already installed, add the optional group with:

```bash
uv tool upgrade "bilibili-cli[audio]"
```

The CLI stores Bilibili account state in `~/.bilibili-cli/`, principally
`credential.json`. `uv` separately manages the isolated executable environment.
Do not put drafts or downloaded media in the credential directory.

Most public reads do not require login. `bili login` is a blocking terminal QR-code
flow: never execute it from an agent. Tell the user to run it in their own
interactive terminal, scan and confirm the QR code, then return after it reports
success.

Any authenticated command can attempt to scan Chrome, Firefox, Edge, and Brave for
cookies when the saved session is absent, stale, or invalid. This can trigger a
browser database or Keychain prompt. Before such a command, tell the user this and
obtain explicit approval; otherwise ask them to validate or log in themselves in an
interactive terminal. Do not ask users to paste cookies or browser secrets.

## Request routing

| User intent | Use |
|---|---|
| Find or inspect public videos and UP 主 profiles | Video, user, search, and discovery read commands |
| Summarize a video | Subtitle first; then AI summary, comments, or optional audio extraction |
| Browse own favorites, following, watch-later, history, or feed | Authenticated account read commands |
| Like, coin, triple, unfollow, post/delete a dynamic, or log out | Write command plus explicit confirmation |
| Download audio for a user-approved transcription workflow | Optional audio command; state exact output path first |

## Version and drift

This reference was written against `bilibili-cli` 0.6.2. Before relying on a newly
introduced option or after upgrading the tool, run:

```bash
bili --version
bili <command> --help
```

If local command help differs from this reference, use local help as the execution
source of truth and update this skill's command reference coherently.
