---
name: web-fetch
description: |
  Use this when you need to fetch and extract readable content from a URL.
  Pairs with web-search: search first to discover URLs, then fetch individual
  pages to retrieve full text content.
---

# Web Fetch

Fetch a web page and extract its readable text content.

## When to Use

- User provides a URL and wants its content read or analyzed
- After a web search returns results, you need to drill into a specific page
- User asks "fetch this page", "get the content from...", "read that link"
- You need the full text of an article, doc page, or blog post

## Parameters

Pass these as arguments when invoking `scripts/fetch.py`:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| url | string | yes | - | Full URL to fetch (must include `https://` or `http://`) |
| max_chars | number | no | 8000 | Maximum characters of text to return |

## Dependencies

- Python packages: `requests`, `beautifulsoup4`
  ```bash
  pip install requests beautifulsoup4
  ```

## Usage

```bash
python scripts/fetch.py "https://example.com/article" [max_chars]
```

Results are returned as structured JSON with `url`, `title`, `text` (readable content),
`status_code`, and `content_type`.

## Pairing with web-search

1. Use **web-search** to discover relevant URLs
2. Use **web-fetch** to retrieve full content from the most promising results
