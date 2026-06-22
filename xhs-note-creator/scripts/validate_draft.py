#!/usr/bin/env python3
"""Validate that a local XHS draft is ready to hand off for publishing."""

from __future__ import annotations

import argparse
import json
import struct
import sys
from pathlib import Path


PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def png_size(path: Path) -> tuple[int, int] | None:
    try:
        header = path.read_bytes()[:24]
    except OSError:
        return None
    if len(header) < 24 or not header.startswith(PNG_SIGNATURE) or header[12:16] != b"IHDR":
        return None
    return struct.unpack(">II", header[16:24])


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate an XHS card draft.")
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
    tags = manifest.get("tags", [])
    if not isinstance(tags, list) or not tags:
        warnings.append("manifest has no tags")

    if cards_path.exists():
        sections = [part.strip() for part in cards_path.read_text(encoding="utf-8").split("\n---\n") if part.strip()]
        for index, section in enumerate(sections, start=1):
            if len(section) > 420:
                warnings.append(f"card {index} has {len(section)} characters; consider splitting it")

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
        "images": [str(image) for image in actual_images],
        "errors": errors,
        "warnings": warnings,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
