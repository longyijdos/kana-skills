---
name: netease-musicbox
description: |
  Use this when the user asks to search, play, pause, resume, stop, skip, seek,
  adjust volume, view lyrics, manage a queue, or log in to NetEase Cloud Music.
  Requires the local `musicbox` CLI from the `netease-musicbox` package.
---

# NetEase MusicBox

Use `musicbox` to control NetEase MusicBox. Before executing any command, read
[`references/command-reference.md`](references/command-reference.md).

## Operating rules

1. Append `--json` to every agent-facing command and parse its `{ok, data}`
   response. Never simulate keypresses in the curses TUI.
2. Search and playback are separate. Never begin audio merely because the user
   asked to search, inspect, or recommend music.
3. A request to play a specified song, playlist, or selected search result
   authorizes playback. After `play`, `next`, or `prev`, wait 1–2 seconds and
   call `musicbox status --json`; do not assume the immediate response proves
   playback started.
4. Playback is a persistent local session owned by `musicboxd`. Control commands
   can start it automatically. Do not stop it after ordinary play, pause, seek,
   queue, or volume commands.
5. When the user says they are done listening, want to close MusicBox, or asks
   to stop listening, stop both playback and the background daemon. Do not stop
   the daemon when the user only asks to pause.
6. Treat `~/.netease-musicbox/` as private local state. It contains
   `cookie.txt` (anonymous or authenticated cookies), configuration, playback
   state, and logs. Never print, move, delete, or edit its files directly.
7. Do not manage `/tmp/netease-musicbox/` directly. It contains the daemon's
   local socket and lock files while MusicBox is in use.
8. Do not repeatedly retry authentication, copyright, verification, or API
   failures. Report the failure and offer the relevant next action.

## Setup

Install the CLI only when `musicbox` is unavailable:

```bash
uv tool install netease-musicbox
```

MusicBox also requires a system playback backend. On macOS install:

```bash
brew install mpg123 mpv
```

`mpg123` supports normal MP3 playback. `mpv` is required for seeking and is
recommended for FLAC and high-resolution audio.

## Login

When a command requires login:

1. Run `musicbox auth login --no-wait --json`.
2. Present the returned terminal QR code and ask the user to scan and confirm it
   with the NetEase Cloud Music app.
3. End the turn. Do not block or poll for the result in the same turn.
4. After the user returns, run `musicbox auth login --check <unikey> --json`.

Do not ask users to provide cookies, passwords, or authentication tokens.

## Version drift

This skill targets NetEase-MusicBox 0.5.2. Before relying on an unfamiliar option
or after an upgrade, verify local behavior:

```bash
musicbox --version
musicbox <command> --help
```

If local command help differs from this reference, use the local help as the
execution source of truth and update this skill and its command reference together.
