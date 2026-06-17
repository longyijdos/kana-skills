"""
kana-skills: web-search
Real-time web search via Tavily API.
"""
import os
import json
import argparse

def search(query: str, max_results: int = 5, include_domains: list[str] | None = None):
    """Execute web search, return structured results."""
    api_key = os.environ.get("TAVILY_API_KEY")
    if not api_key:
        return {"error": "TAVILY_API_KEY not set. Please configure your Tavily API key."}

    try:
        from tavily import TavilyClient
    except ImportError:
        return {"error": "tavily-python not installed. Run: pip install tavily-python"}

    client = TavilyClient(api_key=api_key)

    kwargs = {
        "query": query,
        "max_results": max_results,
        "search_depth": "advanced",
    }
    if include_domains:
        kwargs["include_domains"] = include_domains

    response = client.search(**kwargs)

    results = []
    for r in response.get("results", []):
        results.append({
            "title": r.get("title"),
            "url": r.get("url"),
            "content": r.get("content"),
            "score": r.get("score"),
        })

    return {
        "query": query,
        "count": len(results),
        "results": results,
    }

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Search the web with Tavily.")
    parser.add_argument("query", help="Search query string")
    parser.add_argument("legacy_max_results", nargs="?", type=int, help=argparse.SUPPRESS)
    parser.add_argument("--max-results", type=int, default=None, help="Maximum results to return")
    parser.add_argument(
        "--include-domain",
        action="append",
        dest="include_domains",
        help="Restrict search to a domain. Repeat for multiple domains.",
    )
    args = parser.parse_args()

    max_results = args.max_results or args.legacy_max_results or 5
    result = search(args.query, max_results, args.include_domains)
    print(json.dumps(result, ensure_ascii=False, indent=2))
