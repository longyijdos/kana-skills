"""
kana-skills: web_search
Real-time web search via Tavily API.
"""
import os
import sys
import json

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
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: python search.py <query> [max_results]"}, ensure_ascii=False))
        sys.exit(1)

    query = sys.argv[1]
    max_results = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    result = search(query, max_results)
    print(json.dumps(result, ensure_ascii=False, indent=2))
