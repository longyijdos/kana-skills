---
name: gemini-image-gen
description: |
  Generate new images or edit existing reference images using the Gemini image model
  (gemini-3.1-flash-image) via an OpenAI-compatible endpoint. Supports text-to-image,
  image-to-image (multi-reference editing), aspect ratio, and resolution controls.
---

# Gemini Image Generation & Editing

Use the bundled Python script to generate new illustrations or edit existing reference images using Gemini 3.1 Flash Image via an OpenAI-compatible Chat Completions endpoint.

The script runs with Python 3 pure standard library (zero external dependencies) and reads credentials from `.env` in this skill directory.

## Run

From this skill directory (or passing the relative path to `scripts/generate.py`):

```bash
python3 scripts/generate.py "Prompt description" [options]
```

## Parameters

| Option | Flag | Accepted values | Default | Purpose |
|---|---|---|---:|---|
| `prompt` | Positional or `-p`, `--prompt` | Non-empty text | required | Description of the image to generate or edits to perform. |
| `--ref-image` | `-i`, `-r`, `--ref-images` | One or more file paths | none | Reference image paths for image-to-image generation or editing. |
| `--aspect-ratio` | `-ar` | `1:1`, `16:9`, `9:16`, `4:3`, `3:4` | `1:1` | Desired output image aspect ratio. |
| `--size` | `-s` | `1K`, `2K`, etc. | `1K` | Resolution tier. |
| `--output` | `-o` | File path | `generated_<timestamp>.png` | Destination file path for the output image. |
| `--save-json` | | Flag | disabled | Save raw API response JSON beside the output image. |
| `--timeout` | | Seconds (integer) | `120` | Request timeout in seconds. |

## Examples

### 1. Pure Text-to-Image

Generate a square (1:1) illustration:

```bash
python3 scripts/generate.py "A cute purple-haired anime girl in a retro cyberpunk terminal lab" \
  --aspect-ratio 1:1 \
  --output /tmp/cyberpunk_girl.png
```

Generate a 16:9 wallpaper:

```bash
python3 scripts/generate.py "A tranquil Japanese garden with cherry blossoms at twilight" \
  --aspect-ratio 16:9 \
  --output /tmp/garden.png
```

### 2. Single Reference Image Editing (Image-to-Image)

Modify an existing image (e.g. change time of day, lighting, or background elements):

```bash
python3 scripts/generate.py "Change the room background to a cozy nighttime with moonlit window" \
  --ref-image /path/to/original.png \
  --aspect-ratio 1:1 \
  --output /tmp/night_edit.png
```

### 3. Multi-Reference Image Fusion

Combine elements or styles from multiple images:

```bash
python3 scripts/generate.py "Fuse the subject from ref1 with the art style and lighting of ref2" \
  --ref-image /path/to/subject.png /path/to/style.png \
  --output /tmp/fused_result.png
```

## Output Handling

The script outputs structured JSON to `stdout` and writes decoded image bytes directly to disk (preventing stdout pollution):

```json
{
  "ok": true,
  "output_path": "/path/to/output.png",
  "mime_type": "image/jpeg",
  "bytes": 638792,
  "aspect_ratio": "1:1",
  "image_size": "1K",
  "prompt": "...",
  "reference_images_count": 0,
  "model": "gemini-3.1-flash-image"
}
```

On failure, it outputs `{"ok": false, "error": "..."}` and exits with code 1.

If visual inspection or verification is needed and the agent environment supports image input, inspect the generated image file at `output_path` using the available image observation tool, or return the saved file path directly to the user.

## Configuration

Credentials are read automatically from `gemini-image-gen/.env`:

```ini
GEMINI_IMAGE_API_BASE_URL="https://your-api-endpoint.com/v1"
GEMINI_IMAGE_API_KEY="your-api-key"
GEMINI_IMAGE_MODEL="gemini-3.1-flash-image"
```

If not set in `.env`, the script falls back to `CPA_API_KEY` and default endpoint settings.
