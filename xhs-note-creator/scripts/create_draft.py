#!/usr/bin/env python3
"""Create an ignored, self-contained Xiaohongshu card draft."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parent.parent
DRAFTS_ROOT = SKILL_ROOT / "drafts"


def slug_is_safe(slug: str) -> bool:
    return bool(re.fullmatch(r"[a-z0-9][a-z0-9-]{0,79}", slug))


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a local XHS image-post draft.")
    parser.add_argument("slug", help="Lowercase letters, digits, and hyphens only")
    parser.add_argument("--title", required=True, help="Final note title (20 characters or fewer)")
    parser.add_argument("--subtitle", default="", help="Short cover subtitle")
    parser.add_argument("--theme", choices=("paper", "ink", "coral"), default="paper")
    args = parser.parse_args()

    if not slug_is_safe(args.slug):
        parser.error("slug must use lowercase letters, digits, and hyphens only")
    if len(args.title) > 20:
        parser.error("title must be 20 characters or fewer")

    draft_dir = DRAFTS_ROOT / args.slug
    if draft_dir.exists():
        print(json.dumps({"error": f"draft already exists: {draft_dir}"}, ensure_ascii=False))
        return 1

    (draft_dir / "source").mkdir(parents=True)
    (draft_dir / "output").mkdir()
    manifest = {
        "slug": args.slug,
        "title": args.title,
        "subtitle": args.subtitle,
        "theme": args.theme,
        "tags": [],
        "created_on": date.today().isoformat(),
    }
    (draft_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (draft_dir / "note.md").write_text(
        f"# {args.title}\n\n在这里写最终发布正文。\n\n#小红书 #待补充\n", encoding="utf-8"
    )
    (draft_dir / "cards.md").write_text(
        f"# {args.title}\n\n一句话告诉读者这篇笔记能解决什么问题。\n\n---\n\n# 第 1 步\n\n- 要点一\n- 要点二\n- 要点三\n",
        encoding="utf-8",
    )
    print(json.dumps({"draft_dir": str(draft_dir), "manifest": manifest}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
