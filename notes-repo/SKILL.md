---
name: notes-repo
description: |
  Use this when the user asks to take notes, record information, or edit their
  personal notes repository (such as an Obsidian vault). Locates the repository
  via the KANA_NOTES_REPO environment variable, reads the repository's own
  AGENTS.md or other instruction documents, and follows them.
---

# Notes Repository

Work on the user's personal notes repository. Nothing about the repository is
hardcoded here; discover both its location and its rules at runtime.

## Locate the repository

1. Use a path the user explicitly gives in the conversation, if present.
2. Otherwise read the `KANA_NOTES_REPO` environment variable.
3. If neither exists, ask the user for the path. Do not guess or search the
   filesystem.

Confirm the path exists before doing anything.

## Read the repository's instructions

Before any write, find and read the repository's own guidance:

1. `AGENTS.md` at the repository root, if present.
2. Other instruction or convention documents it points to or that exist in the
   repository (for example a `.agents/` directory, `CONTRIBUTING.md`, a local
   style guide).

## Follow the repository's instructions

Do what the repository documents: its git workflow (direct commits vs. branch and
pull request), layout, style rules, and edit boundaries. The repository's rules win
over anything in this skill.

If the repository documents no workflow, ask the user how they want changes handled
before writing.
