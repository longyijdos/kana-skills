---
name: web-fetch
description: |
  Use this when you need to fetch and extract readable content from a URL.
  Trigger when the task already has a specific URL or link whose page text
  needs to be read, summarized, inspected, or analyzed.
---

# Web Fetch

Use the bundled script to fetch a known URL and extract readable text.

## Parameters

Pass these as arguments when invoking `scripts/fetch.py`:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| url | string | yes | - | Full URL to fetch (must include `https://` or `http://`) |
| max_chars | number | no | 8000 | Maximum characters of text to return |
| max_bytes | number | no | 5242880 | Maximum response bytes to read |

## Dependencies

- Python packages: `requests`, `beautifulsoup4`
  ```bash
  pip install requests beautifulsoup4
  ```

## Run

```bash
python scripts/fetch.py "https://example.com/article" [--max-chars 8000] [--max-bytes 5242880]
```

Results are returned as structured JSON with `url`, `title`, `text` (readable content),
`status_code`, `content_type`, `final_url`, `content_length`, `bytes_read`, `limited`,
and `truncated`.

This skill does not discover URLs. Use it only after the URL is known.

## Handling Results

- Treat `text` as extracted page content and mention when `truncated` is true.
- For non-HTML responses, the script returns raw response text up to `max_chars`.
- Use `final_url` when redirects matter.
- When `limited` is true, the response body hit `max_bytes`; say that the fetched content is partial.
- If the URL lacks `http://` or `https://`, ask for or construct the full URL before retrying.
- This script does not render JavaScript and does not extract text from PDFs.
- If the script returns an `error`, report the fetch, HTTP, dependency, or URL validation failure directly.
