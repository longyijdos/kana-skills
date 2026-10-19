---
name: xhs-note-creator
description: |
  Use this to turn approved Xiaohongshu (小红书, XHS) post ideas, the user's own
  screenshots or code, and their notes into a local, reviewable image-post draft.
  Layouts: real screenshots, ray.so-style code windows, a one-item-per-page
  roundup, or plain text. Creates publishing assets only; it never logs into
  Xiaohongshu, uploads images, or publishes a note.
---

# XHS Note Creator

Create a self-contained local draft for one Xiaohongshu image post. The resulting
images are inputs to the separate `xiaohongshu-cli` skill; do not invoke `xhs post`
from this skill.

Posts that do well in tech and tools categories are built from real material:
screenshots, screen recordings, terminal output, and first-person notes. Designed
text cards are the exception. Before writing anything, read
`references/style-guide.md`; it lists what makes a post read as machine-written.

## Local layout

Keep all user-created materials in `drafts/`, which is intentionally ignored by Git:

```text
drafts/<slug>/
├── manifest.json      # layout, theme, title, subtitle, tags
├── note.md            # final Xiaohongshu body copy
├── cards.md           # page content, separated by --- lines
├── source/            # the user's screenshots, icons, and notes
└── output/
    ├── cover.png
    └── card-01.png ...
```

Never place drafts in `~/.xiaohongshu-cli/`; that directory contains account cookies
and transient CLI state.

## One-time renderer setup

From this skill directory:

```bash
npm install
npx playwright install chromium
```

## Workflow

### 1. Collect material and pick a layout

Ask the user what real material they have before choosing a layout, and copy it into
`source/`. If they have none for a tool or app post, suggest taking a few screenshots
first rather than falling back to text cards.

| Layout | Use when | Every page needs |
| --- | --- | --- |
| `screenshots` (default) | Showing an app, a tool's result, before/after | an image line |
| `code` | Commands, config, short snippets | a fenced code block |
| `collection` | Recommending several apps or projects | `# Name` plus an icon image; a page without an image becomes a summary page |
| `text` | Opinion or story with no visual material | headings and short paragraphs |

Ask for the user's own experience with the topic (why they made or use it, what
went wrong, what they actually use) when the material does not already contain it.
Do not invent experiences, numbers, or star counts.

### 2. Create the draft

```bash
python scripts/create_draft.py "2026-06-22-shell-guide" \
  --title "终端里每天都在用的 3 个小操作" \
  --layout code --theme sunset
```

Themes: `screenshots` light / dark / blur, `code` sunset / breeze / mono,
`collection` paper, `text` paper / ink.

Manifest options: `cover: false` skips the cover (raw-screenshot posts often do
well without one); `cover_image` picks the screenshots cover image (defaults to the
first page image); `kicker` and `cover_note` add the small label and footer on a
collection cover.

### 3. Write cards.md

Pages are separated by a `---` line. Image paths are relative to the draft.

- `screenshots`: `![](source/shot.png)`, optional `# title`, optional one-line caption.
  Landscape screenshots leave empty space in 3:4; crop to the relevant area when it helps.
- `code`: a fence like ```` ```zsh Window title ````, comments in the user's own words,
  lines up to about 40 characters, optional one or two sentences below the block.
- `collection`: `# Name`, `![](source/icon.png)`, `meta: category`, `## one-line summary`,
  a sentence of personal use, `tags: a, b`. A final page with `- need → item` rows
  renders as a comparison table.
- `text`: `# heading` and short paragraphs, one idea per page, `> quote` for one key line.

Text is scaled automatically to fill the page without overflowing.

### 4. Render and look at the result

```bash
node scripts/render_cards.js --draft "drafts/2026-06-22-shell-guide"
```

Open the PNGs and check them visually before handing off.

### 5. Validate

```bash
python scripts/validate_draft.py "drafts/2026-06-22-shell-guide"
```

Errors: missing files, missing referenced images, title over 20 characters, image
count outside 1–9, wrong image size, pages that do not match the layout. Warnings:
stock phrases, emoji used as decoration or list markers, long code lines, dense pages,
missing tags. Fix warnings by rewriting, not by rewording around the check.

### 6. Hand off

Report the exact local paths for `manifest.json`, `note.md`, and the output images.
Use the separate `xiaohongshu-cli` skill only if the user later asks to publish. That
skill must show the final title, body, image list, and privacy setting and obtain
explicit confirmation before publishing.

## Limits

- Title 20 characters or fewer; at most 9 images including the cover.
- Never claim that a card has been uploaded or published; this skill has no account
  access and performs no network requests to Xiaohongshu.
