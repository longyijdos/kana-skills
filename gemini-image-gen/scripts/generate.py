#!/usr/bin/env python3
"""
Gemini Image Generation & Editing CLI
Uses an OpenAI-compatible Chat Completions endpoint (e.g. CLIProxyAPI)
with the gemini-3.1-flash-image model.
Pure standard library, zero external dependencies.
"""

import argparse
import base64
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


def load_dotenv(skill_root: Path):
    """Load key-value pairs from .env into os.environ if not already present."""
    candidates = [
        skill_root / ".env",
        skill_root.parent / ".env",
        Path.cwd() / ".env",
    ]
    for env_path in candidates:
        if env_path.is_file():
            try:
                with open(env_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith("#") or "=" not in line:
                            continue
                        key, val = line.split("=", 1)
                        key = key.strip()
                        val = val.strip().strip("'\"")
                        if key:
                            os.environ[key] = val
                break
            except Exception:
                pass


def guess_mime_type(path: Path) -> str:
    ext = path.suffix.lower()
    if ext in (".jpg", ".jpeg"):
        return "image/jpeg"
    if ext == ".png":
        return "image/png"
    if ext == ".webp":
        return "image/webp"
    return "image/jpeg"


def main():
    parser = argparse.ArgumentParser(
        description="Generate or edit images using Gemini 3.1 Flash Image via an OpenAI-compatible endpoint."
    )
    parser.add_argument(
        "prompt",
        nargs="?",
        default="",
        help="Text prompt describing the desired image or modifications.",
    )
    parser.add_argument(
        "-p", "--prompt",
        dest="prompt_flag",
        default="",
        help="Alternative flag to specify prompt.",
    )
    parser.add_argument(
        "-i", "-r", "--ref-image", "--ref-images",
        dest="ref_images",
        nargs="*",
        default=[],
        help="Optional paths to one or more reference images for image-to-image generation.",
    )
    parser.add_argument(
        "-ar", "--aspect-ratio",
        dest="aspect_ratio",
        default="1:1",
        choices=["1:1", "16:9", "9:16", "4:3", "3:4"],
        help="Image aspect ratio. Choices: 1:1, 16:9, 9:16, 4:3, 3:4. Default: 1:1.",
    )
    parser.add_argument(
        "-s", "--size",
        dest="size",
        default="1K",
        help="Image resolution tier, e.g. 1K. Default: 1K.",
    )
    parser.add_argument(
        "-o", "--output",
        dest="output",
        default="",
        help="Path where the output image should be saved. Default: generated_<timestamp>.png",
    )
    parser.add_argument(
        "--save-json",
        dest="save_json",
        action="store_true",
        help="Save raw API response JSON beside output image.",
    )
    parser.add_argument(
        "--timeout",
        dest="timeout",
        type=int,
        default=120,
        help="HTTP request timeout in seconds. Default: 120.",
    )

    args = parser.parse_args()

    # Determine prompt
    prompt = (args.prompt or args.prompt_flag).strip()
    if not prompt:
        error_res = {"ok": False, "error": "Prompt must not be empty. Provide via positional argument or --prompt."}
        print(json.dumps(error_res, ensure_ascii=False, indent=2))
        sys.exit(1)

    skill_root = Path(__file__).resolve().parent.parent
    load_dotenv(skill_root)

    # API Configuration
    base_url = (
        os.environ.get("GEMINI_IMAGE_API_BASE_URL")
        or os.environ.get("IMAGE_API_BASE_URL")
        or os.environ.get("CPA_BASE_URL")
    )

    api_key = (
        os.environ.get("GEMINI_IMAGE_API_KEY")
        or os.environ.get("IMAGE_API_KEY")
        or os.environ.get("CPA_API_KEY")
    )

    model = (
        os.environ.get("GEMINI_IMAGE_MODEL")
        or os.environ.get("IMAGE_MODEL")
        or "gemini-3.1-flash-image"
    )

    if not base_url:
        error_res = {
            "ok": False,
            "error": "Missing Base URL. Set GEMINI_IMAGE_API_BASE_URL in .env or environment.",
        }
        print(json.dumps(error_res, ensure_ascii=False, indent=2))
        sys.exit(1)
    base_url = base_url.rstrip("/")

    if not api_key:
        error_res = {
            "ok": False,
            "error": "Missing API Key. Set GEMINI_IMAGE_API_KEY (or CPA_API_KEY) in .env or environment.",
        }
        print(json.dumps(error_res, ensure_ascii=False, indent=2))
        sys.exit(1)

    # Build content
    content = []
    resolved_ref_images = []
    if args.ref_images:
        for img_str in args.ref_images:
            p = Path(img_str).expanduser().resolve()
            if not p.is_file():
                error_res = {"ok": False, "error": f"Reference image file not found: {p}"}
                print(json.dumps(error_res, ensure_ascii=False, indent=2))
                sys.exit(1)
            mime_type = guess_mime_type(p)
            try:
                with open(p, "rb") as f:
                    b64_data = base64.b64encode(f.read()).decode("utf-8")
                content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:{mime_type};base64,{b64_data}"
                    }
                })
                resolved_ref_images.append(str(p))
            except Exception as e:
                error_res = {"ok": False, "error": f"Failed reading reference image {p}: {e}"}
                print(json.dumps(error_res, ensure_ascii=False, indent=2))
                sys.exit(1)

    content.append({
        "type": "text",
        "text": prompt
    })

    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": content
            }
        ],
        "modalities": ["image"],
        "image_config": {
            "aspect_ratio": args.aspect_ratio,
            "image_size": args.size
        }
    }

    req_url = f"{base_url}/chat/completions"
    req_body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        req_url,
        data=req_body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=args.timeout) as resp:
            status = resp.status
            resp_bytes = resp.read()
            resp_data = json.loads(resp_bytes.decode("utf-8"))
    except urllib.error.HTTPError as e:
        err_msg = e.read().decode("utf-8", errors="replace")
        error_res = {
            "ok": False,
            "error": f"HTTP {e.code}: {err_msg}",
            "status_code": e.code
        }
        print(json.dumps(error_res, ensure_ascii=False, indent=2))
        sys.exit(1)
    except Exception as e:
        error_res = {"ok": False, "error": f"Network or request error: {e}"}
        print(json.dumps(error_res, ensure_ascii=False, indent=2))
        sys.exit(1)

    images = resp_data.get("choices", [{}])[0].get("message", {}).get("images", [])
    if not images or not images[0].get("image_url", {}).get("url"):
        error_res = {
            "ok": False,
            "error": "No image returned in response payload.",
            "response_preview": str(resp_data)[:500]
        }
        print(json.dumps(error_res, ensure_ascii=False, indent=2))
        sys.exit(1)

    img_url = images[0]["image_url"]["url"]
    match = re.match(r"^data:(image\/\w+);base64,(.+)$", img_url, re.DOTALL)
    if not match:
        error_res = {"ok": False, "error": "Invalid data URL format in returned image."}
        print(json.dumps(error_res, ensure_ascii=False, indent=2))
        sys.exit(1)

    mime_type = match.group(1)
    raw_b64 = match.group(2)
    img_bytes = base64.b64decode(raw_b64)

    # Determine output path
    if args.output:
        out_path = Path(args.output).expanduser().resolve()
    else:
        timestamp = int(time.time())
        ext = ".png"
        out_path = Path.cwd() / f"generated_{timestamp}{ext}"

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "wb") as f:
        f.write(img_bytes)

    if args.save_json:
        json_path = out_path.with_suffix(".json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(resp_data, f, ensure_ascii=False, indent=2)

    result = {
        "ok": True,
        "output_path": str(out_path),
        "mime_type": mime_type,
        "bytes": len(img_bytes),
        "aspect_ratio": args.aspect_ratio,
        "image_size": args.size,
        "prompt": prompt,
        "reference_images_count": len(resolved_ref_images),
        "model": model
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
