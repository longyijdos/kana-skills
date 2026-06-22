---
name: xiaohongshu-cli
description: |
  Use this for all Xiaohongshu (小红书, XHS, Redbook) account operations: searching
  and reading notes, comments, users, trends, favorites, notifications, and own
  posts; and, only with explicit confirmation, liking, collecting, following,
  commenting, replying, deleting, or publishing. Requires the local xhs CLI.
---

# Xiaohongshu CLI

Use `xhs`, provided by the `xiaohongshu-cli` package. This skill manages Xiaohongshu
account operations only. Use the separate `xhs-note-creator` skill to create and
validate card images before publishing an image note.

Before executing any `xhs` command, read
[`references/command-reference.md`](references/command-reference.md). It is the
canonical command map, parameter reference, cache guide, and error-handling guide
for this skill.

## Operating rules

1. Prefer machine-readable output: append `--json` to every command.
2. Run requests serially. Do not parallelize `xhs` calls, scrape in bulk, or retry
   around verification and rate-limit errors.
3. Treat cookies, `xsec_token` values, and account-state files as secrets. Never
   request them in chat or print them in summaries or logs.
4. For a read request, use the smallest number of calls that answers the question;
   use a full note URL when one is supplied.
5. For a write request, first show the exact target, final text, image paths, topics,
   visibility, and command effect. Obtain explicit confirmation in the current
   conversation immediately before execution.
6. A general request such as “publish this” does not authorize a later changed title,
   body, topic list, image set, or visibility setting.

## Setup and authentication

Install the CLI only when `xhs` is unavailable:

```bash
uv tool install xiaohongshu-cli
```

The CLI stores account state outside this repository in `~/.xiaohongshu-cli/`.
It can contain saved cookies and short-lived caches. Do not put drafts or rendered
images there.

Never begin a first login with bare `xhs status` or bare `xhs login`: with no saved
session they can auto-scan installed browsers and trigger repeated macOS Keychain
prompts. Follow the authentication decision tree in the command reference instead.

## Request routing

| User intent | Use |
|---|---|
| Find, inspect, or analyze public notes | Reading and discovery commands |
| Inspect a profile, own posts, favorites, notifications, or unread counts | Account and creator read commands |
| Read a comment thread or replies | Comment commands |
| Like, collect, follow, comment, reply, or delete | Write command plus explicit confirmation |
| Produce cover/card images or post copy | `xhs-note-creator`, then validate the draft |
| Publish a prepared image post | Creator command plus explicit confirmation; default private |

## Handoff to publishing

For a post produced by `xhs-note-creator`, validate the draft first. Then show the
user the final `manifest.json` title, `note.md` body, complete `output/*.png` list,
topics, and visibility. Publish only after confirmation, using the exact image list.

The CLI supports image notes only: it uploads existing image files and does not
generate cards, convert source material into images, publish text-only notes, or
publish video notes.

## Version and drift

This reference was written against `xiaohongshu-cli` 0.6.4. Before relying on a
newly introduced option or after upgrading the tool, run:

```bash
xhs --version
xhs <command> --help
```

If CLI behavior differs from this reference, use the local command help as the
execution source of truth and update this skill's command reference coherently.
