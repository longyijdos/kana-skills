---
name: xhs-note-creator
description: |
  Use this to turn approved Xiaohongshu (小红书, XHS) post ideas, source material,
  and copy into a local, reviewable draft with a cover and PNG text cards. This
  skill creates publishing assets only; it never logs into Xiaohongshu, uploads
  images, or publishes a note.
---

# XHS Note Creator

Create a self-contained local draft for one Xiaohongshu image post. The resulting
images are inputs to the separate `xiaohongshu-cli` skill; do not invoke `xhs post`
from this skill.

## Local layout

Keep all user-created materials in `drafts/`, which is intentionally ignored by Git:

```text
drafts/<slug>/
├── manifest.json      # title, subtitle, theme, tags, and post metadata
├── note.md            # final Xiaohongshu body copy
├── cards.md           # text-card content, separated into pages with ---
├── source/            # user-supplied source images or notes
└── output/
    ├── cover.png
    ├── card-01.png
    └── card-02.png
```

Never place drafts in `~/.xiaohongshu-cli/`; that directory contains account cookies
and transient CLI state.

## One-time renderer setup

From this skill directory:

```bash
npm install
npx playwright install chromium
```

This installs the local rendering dependency and browser runtime. It does not log in
to Xiaohongshu or access browser cookies.

## Workflow

### 1. Create a draft

Choose a stable, filesystem-safe slug and create the local draft structure:

```bash
python scripts/create_draft.py "2026-06-22-shell-guide" \
  --title "再也不用手搓复杂 shell 命令了" \
  --subtitle "3 个高频场景直接复制"
```

Edit these files before rendering:

- `manifest.json`: final title, subtitle, theme, and tags.
- `note.md`: final publish-body copy, including line breaks and hashtags.
- `cards.md`: visual card text. It is deliberately separate from `note.md`.

Each `---` on its own line in `cards.md` creates a new image card. Keep one card
focused on one idea and under roughly 300 Chinese characters. Use short headings,
short paragraphs, bullets, and code snippets; do not place raw URLs or dense walls
of text in the card copy.

### 2. Render local assets

```bash
node scripts/render_cards.js --draft "drafts/2026-06-22-shell-guide"
```

The renderer creates a 1080×1440 `cover.png` and one 1080×1440 PNG per non-empty
card section. Supported themes are `paper`, `ink`, and `coral`.

### 3. Validate before handoff

```bash
python scripts/validate_draft.py "drafts/2026-06-22-shell-guide"
```

Validation fails when required files are missing, the title exceeds 20 characters,
the rendered image count is not 1–9, or any generated image is not 1080×1440.
Warnings identify dense card copy or missing tags.

### 4. Handoff only

After validation, report the exact local paths for:

- `manifest.json`
- `note.md`
- `output/cover.png` and `output/card-*.png`

Use the separate `xiaohongshu-cli` skill only if the user later asks to publish. That
skill must show the final title, body, image list, and privacy setting and obtain
explicit confirmation before publishing.

## Content requirements

- Keep the title at 20 characters or fewer.
- Make the cover title concise; its purpose is scanning, not full explanation.
- Use 1–8 body cards, so cover plus body stays within Xiaohongshu's 9-image limit.
- Treat generated cards as a draft: inspect them visually before publishing.
- Never claim that a card has been uploaded or published; this skill has no account
  access and performs no network requests to Xiaohongshu.
