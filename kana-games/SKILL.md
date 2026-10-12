---
name: kana-games
description: Entry point for kana-games, turn-based games (大话骰 / liar's dice, 五子棋 / gomoku, or custom games) between the user in a browser and the Agent on a CLI. Use when the user wants to play a game with the Agent or create one, and the kana-games-play skill is not available yet.
---

# kana-games

This skill only installs and hands off. The rules, commands, and play loop
live in the `kana-games` npm package and its own skills; follow those, not
memory. If the `kana-games-play` (playing) or `kana-games-create` (making a
game) skill is already available, use it instead of this one.

## 1. Make sure the CLI is installed

```sh
kana-games --version
```

If the command is missing, ask the user before installing (Node.js 22.18+):

```sh
npm install --global kana-games
```

## 2. Install the full skills for this Agent

```sh
kana-games install claude    # Claude Code
kana-games install codex     # Codex
kana-games install kana      # Kana
kana-games install <dir>     # any other Agent: its skill directory
```

This adds `kana-games-play`, `kana-games-create`, and, for Claude Code, Codex
and Kana, the `kana-games-player` companion subagent. Existing copies are kept;
add `--force` after upgrading kana-games. Kana additionally needs the skills
enabled in `/skills`.

## 3. Continue in this session

Newly installed skills and subagents usually load only after the Agent
restarts. Do not wait for that: run `npm root -g`, then read and follow

- `<npm root>/kana-games/skills/kana-games-play/SKILL.md` to play, or
- `<npm root>/kana-games/skills/kana-games-create/SKILL.md` to build a game.

Tell the user that after restarting, the Agent can hand matches to the
`kana-games-player` subagent and keep the conversation free.

Project: <https://github.com/longyijdos/kana-games>
