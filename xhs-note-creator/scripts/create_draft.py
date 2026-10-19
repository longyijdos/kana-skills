#!/usr/bin/env python3
"""Create an ignored, self-contained Xiaohongshu image-post draft."""

from __future__ import annotations

import argparse
import json
import re
from datetime import date
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parent.parent
DRAFTS_ROOT = SKILL_ROOT / "drafts"

LAYOUT_THEMES = {
    "screenshots": ("light", "dark", "blur"),
    "code": ("sunset", "breeze", "mono"),
    "collection": ("paper",),
    "text": ("paper", "ink"),
}

CARD_TEMPLATES = {
    "screenshots": (
        "![](source/01.png)\n\n一句话说明这张图里发生了什么\n\n---\n\n"
        "![](source/02.png)\n\n可以不写说明，只放图\n"
    ),
    "code": (
        "```zsh 窗口标题\n# 注释写成你自己的话\ncommand --flag value\n```\n\n"
        "图下面可以补一句为什么这样用。\n\n---\n\n"
        "```zsh 第二个例子\ncommand two\n```\n"
    ),
    "collection": (
        "# 项目名\n![](source/icon.png)\nmeta: 分类或一个可核实的数字\n"
        "## 一句话说明它是什么\n一句你自己的使用体验。\ntags: 标签一, 标签二\n\n---\n\n"
        "# 按需求选\n\n- 场景 → 项目名\n"
    ),
    "text": "# 小标题\n\n一段话只讲一件事。\n\n---\n\n# 第二页\n\n短句，换行，留白。\n",
}


def slug_is_safe(slug: str) -> bool:
    return bool(re.fullmatch(r"[a-z0-9][a-z0-9-]{0,79}", slug))


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a local XHS image-post draft.")
    parser.add_argument("slug", help="Lowercase letters, digits, and hyphens only")
    parser.add_argument("--title", required=True, help="Final note title (20 characters or fewer)")
    parser.add_argument("--subtitle", default="", help="Short cover subtitle")
    parser.add_argument("--layout", choices=tuple(LAYOUT_THEMES), default="screenshots")
    parser.add_argument("--theme", help="Layout theme; defaults to the layout's first theme")
    args = parser.parse_args()

    if not slug_is_safe(args.slug):
        parser.error("slug must use lowercase letters, digits, and hyphens only")
    if len(args.title) > 20:
        parser.error("title must be 20 characters or fewer")
    themes = LAYOUT_THEMES[args.layout]
    theme = args.theme or themes[0]
    if theme not in themes:
        parser.error(f"theme for {args.layout} must be one of: {', '.join(themes)}")

    draft_dir = DRAFTS_ROOT / args.slug
    if draft_dir.exists():
        print(json.dumps({"error": f"draft already exists: {draft_dir}"}, ensure_ascii=False))
        return 1

    (draft_dir / "source").mkdir(parents=True)
    (draft_dir / "output").mkdir()
    manifest = {
        "slug": args.slug,
        "layout": args.layout,
        "theme": theme,
        "title": args.title,
        "subtitle": args.subtitle,
        "cover": True,
        "tags": [],
        "created_on": date.today().isoformat(),
    }
    if args.layout == "screenshots":
        manifest["cover_image"] = ""
    if args.layout == "collection":
        manifest["kicker"] = ""
        manifest["cover_note"] = ""
    (draft_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (draft_dir / "note.md").write_text("在这里写最终发布正文。\n\n#待补充\n", encoding="utf-8")
    (draft_dir / "cards.md").write_text(CARD_TEMPLATES[args.layout], encoding="utf-8")
    print(json.dumps({"draft_dir": str(draft_dir), "manifest": manifest}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
