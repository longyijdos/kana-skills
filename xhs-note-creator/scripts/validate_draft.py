#!/usr/bin/env python3
"""Validate that a local XHS draft is ready to hand off for publishing."""

from __future__ import annotations

import argparse
import json
import re
import struct
from pathlib import Path


PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
LAYOUTS = ("screenshots", "code", "collection", "text")

# Stock phrases that make a post read as machine-written; see references/style-guide.md.
STOCK_PHRASES = (
    "破防", "绝绝子", "yyds", "宝子", "家人们", "姐妹们", "保姆级", "神器", "神仙", "天花板",
    "丝滑", "炸裂", "封神", "必备", "干货满满", "建议收藏", "收藏不迷路", "不吃亏", "不迷路",
    "最佳选择", "一键搞定", "搞定一切", "效率翻倍", "告别", "亮点", "强烈推荐", "赶紧",
)
EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿⭐✅❌️]")
EMOJI_NUMBER = re.compile("[0-9]️?⃣")
IMAGE_LINE = re.compile(r"^!\[[^\]]*\]\(([^)]+)\)\s*$", re.M)


def png_size(path: Path) -> tuple[int, int] | None:
    try:
        header = path.read_bytes()[:24]
    except OSError:
        return None
    if len(header) < 24 or not header.startswith(PNG_SIGNATURE) or header[12:16] != b"IHDR":
        return None
    return struct.unpack(">II", header[16:24])


def split_pages(markdown: str) -> list[str]:
    pages, current, fenced = [], [], False
    for line in markdown.splitlines():
        if line.strip().startswith("```"):
            fenced = not fenced
        if not fenced and re.fullmatch(r"---\s*", line):
            pages.append("\n".join(current))
            current = []
        else:
            current.append(line)
    pages.append("\n".join(current))
    return [page.strip() for page in pages if page.strip()]


def style_warnings(name: str, text: str) -> list[str]:
    warnings = []
    found = sorted({phrase for phrase in STOCK_PHRASES if phrase.lower() in text.lower()})
    if found:
        warnings.append(f"{name} uses stock phrases: {', '.join(found)}")
    emoji_count = len(EMOJI.findall(text)) + len(EMOJI_NUMBER.findall(text))
    if emoji_count > 3:
        warnings.append(f"{name} has {emoji_count} emoji; keep it to 3 or fewer")
    if EMOJI_NUMBER.search(text) or re.search(r"^\s*✅", text, re.M):
        warnings.append(f"{name} uses emoji as list markers")
    return warnings


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate an XHS image-post draft.")
    parser.add_argument("draft", type=Path)
    args = parser.parse_args()
    draft = args.draft.resolve()
    errors: list[str] = []
    warnings: list[str] = []

    manifest_path = draft / "manifest.json"
    note_path = draft / "note.md"
    cards_path = draft / "cards.md"
    if not manifest_path.exists():
        errors.append("missing manifest.json")
        manifest = {}
    else:
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            errors.append("manifest.json is not valid JSON")
            manifest = {}
    for required in (note_path, cards_path):
        if not required.exists():
            errors.append(f"missing {required.name}")

    title = str(manifest.get("title", "")).strip()
    if not title:
        errors.append("manifest title is required")
    elif len(title) > 20:
        errors.append("manifest title exceeds 20 characters")
    layout = manifest.get("layout", "text")
    if layout not in LAYOUTS:
        errors.append(f"unknown layout {layout!r}")
    tags = manifest.get("tags", [])
    if not isinstance(tags, list) or not tags:
        warnings.append("manifest has no tags")
    elif len(tags) > 8:
        warnings.append(f"manifest has {len(tags)} tags; 3-8 relevant tags read more naturally")

    if note_path.exists():
        warnings.extend(style_warnings("note.md", note_path.read_text(encoding="utf-8")))

    if cards_path.exists():
        cards = cards_path.read_text(encoding="utf-8")
        warnings.extend(style_warnings("cards.md", cards))
        for src in IMAGE_LINE.findall(cards) + ([manifest["cover_image"]] if manifest.get("cover_image") else []):
            if not (draft / src).exists():
                errors.append(f"referenced image not found: {src}")
        pages = split_pages(cards)
        for index, page in enumerate(pages, start=1):
            has_image = bool(IMAGE_LINE.search(page))
            if layout == "screenshots" and not has_image:
                errors.append(f"page {index}: screenshots layout needs an image on every page")
            if layout == "code" and "```" not in page:
                errors.append(f"page {index}: code layout needs a fenced code block")
            if layout == "code":
                long_lines = [line for line in page.splitlines() if len(line) > 44 and not line.startswith("```")]
                if long_lines:
                    warnings.append(f"page {index}: {len(long_lines)} code line(s) over 44 characters will wrap")
            prose = re.sub(r"```.*?```", "", page, flags=re.S)
            if layout in ("text", "collection") and len(prose) > 300:
                warnings.append(f"page {index} has {len(prose)} characters; consider splitting it")
        if layout == "text":
            warnings.append("text layout has no real images; screenshots or code pages usually read better")

    output = draft / "output"
    images = [output / "cover.png", *sorted(output.glob("card-*.png"))]
    actual_images = [image for image in images if image.exists()]
    if not 1 <= len(actual_images) <= 9:
        errors.append(f"expected 1-9 rendered images, found {len(actual_images)}")
    for image in actual_images:
        size = png_size(image)
        if size is None:
            errors.append(f"{image.name} is not a readable PNG")
        elif size != (1080, 1440):
            errors.append(f"{image.name} is {size[0]}x{size[1]}, expected 1080x1440")

    result = {
        "valid": not errors,
        "draft": str(draft),
        "layout": layout,
        "images": [str(image) for image in actual_images],
        "errors": errors,
        "warnings": warnings,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
