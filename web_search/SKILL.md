---
name: web-search
description: |
  Use this when you need to search the web for real-time information,
  recent news, documentation, or any topic requiring up-to-date results.
  Powered by Tavily Search API.
---

# Web Search

Real-time web search skill via Tavily API.

## When to Use

- User needs current information beyond your knowledge cutoff
- Searching for recent news, docs, or real-time data
- User explicitly asks to "search", "look up", or "find online"

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

## Usage

```bash
python scripts/search.py "your query" [max_results]
```

Results are returned as structured JSON with title, url, content, and relevance score.
