---
name: web-search
description: |
  Use this when you need to search the web for real-time information,
  recent news, documentation, or any topic requiring up-to-date search results.
  Uses Tavily Search API and returns structured result summaries with URLs.
---

# Web Search

Use the bundled script to search Tavily and return structured result summaries.

## Parameters

Pass these as arguments when invoking `scripts/search.py`:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| query | string | yes | - | Search query string |
| max_results | number | no | 5 | Max results to return |
| include_domains | string[] | no | - | Restrict to specific domains |

## Dependencies

- `TAVILY_API_KEY` environment variable
- Python package: `tavily-python` (`pip install tavily-python`)

## Run

```bash
python scripts/search.py "your query" [--max-results 5] [--include-domain example.com]
```

Repeat `--include-domain` to allow multiple domains. Results are returned as structured
JSON with `title`, `url`, `content`, and `score`.

## Handling Results

- Use `content` as a search-result snippet, not as full page text.
- Preserve URLs in the final answer when the user needs sources.
- If a result needs direct inspection, use an appropriate URL-reading capability on that specific URL.
- If the script returns an `error`, report the missing dependency, missing `TAVILY_API_KEY`, or API failure directly.
