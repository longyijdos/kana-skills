"""Search the web with Tavily and emit a bounded, agent-friendly JSON result."""

import argparse
import json
import os
import sys
from typing import Any


DEFAULT_MAX_RESULTS = 5
MAX_RESULTS = 20
MAX_SNIPPET_CHARS = 1_200
MAX_TIMEOUT_SECONDS = 120


def error_result(code: str, message: str, *, retryable: bool = False) -> dict[str, Any]:
    return {
        "ok": False,
        "error": {
            "code": code,
            "message": message,
            "retryable": retryable,
        },
    }


def is_retryable_error(message: str) -> bool:
    normalized = message.lower()
    return any(
        marker in normalized
        for marker in (
            "timeout",
            "timed out",
            "connection",
            "temporar",
            "rate limit",
            "too many requests",
            "429",
            "500",
            "502",
            "503",
            "504",
        )
    )


def bounded_text(value: Any, max_chars: int) -> tuple[str | None, bool]:
    if value is None:
        return None, False
    text = str(value).strip()
    if len(text) <= max_chars:
        return text, False
    return text[:max_chars].rstrip() + "...", True


def search(
    query: str,
    *,
    max_results: int = DEFAULT_MAX_RESULTS,
    auto_parameters: bool = True,
    depth: str | None = None,
    topic: str | None = None,
    time_range: str | None = None,
    include_domains: list[str] | None = None,
    exclude_domains: list[str] | None = None,
    timeout: float = 60,
) -> dict[str, Any]:
    """Execute a Tavily search and normalize the provider response."""
    query = query.strip()
    if not query:
        return error_result("invalid_query", "query must not be empty")
    if not 1 <= max_results <= MAX_RESULTS:
        return error_result(
            "invalid_max_results",
            f"max_results must be between 1 and {MAX_RESULTS}",
        )
    if not 0 < timeout <= MAX_TIMEOUT_SECONDS:
        return error_result(
            "invalid_timeout",
            f"timeout must be greater than 0 and no more than {MAX_TIMEOUT_SECONDS} seconds",
        )

    api_key = os.environ.get("TAVILY_API_KEY")
    if not api_key:
        return error_result(
            "missing_api_key",
            "TAVILY_API_KEY is not set. Configure the Tavily API key before searching.",
        )

    try:
        from tavily import TavilyClient
    except ImportError:
        return error_result(
            "missing_dependency",
            "tavily-python is not installed. Run: python -m pip install -r requirements.txt",
        )

    kwargs: dict[str, Any] = {
        "query": query,
        "max_results": max_results,
        "timeout": timeout,
        "auto_parameters": auto_parameters,
    }
    if depth:
        kwargs["search_depth"] = depth
    if topic:
        kwargs["topic"] = topic
    if time_range:
        kwargs["time_range"] = time_range
    if include_domains:
        kwargs["include_domains"] = include_domains
    if exclude_domains:
        kwargs["exclude_domains"] = exclude_domains

    try:
        response = TavilyClient(api_key=api_key).search(**kwargs)
    except Exception as exc:  # Provider exceptions vary across SDK releases.
        message = str(exc).replace(api_key, "[REDACTED]")
        return error_result(
            "search_failed",
            f"Tavily search failed ({type(exc).__name__}): {message}",
            retryable=is_retryable_error(message),
        )

    results = []
    for item in response.get("results", []):
        snippet, snippet_truncated = bounded_text(item.get("content"), MAX_SNIPPET_CHARS)
        result = {
            "title": item.get("title"),
            "url": item.get("url"),
            "snippet": snippet,
            "score": item.get("score"),
        }
        if item.get("published_date"):
            result["published_date"] = item["published_date"]
        if snippet_truncated:
            result["snippet_truncated"] = True
        results.append(result)

    return {
        "ok": True,
        "provider": "tavily",
        "query": query,
        "count": len(results),
        "requested_parameters": {
            "auto_parameters": auto_parameters,
            "search_depth": depth,
            "topic": topic,
            "time_range": time_range,
            "include_domains": include_domains or [],
            "exclude_domains": exclude_domains or [],
            "max_results": max_results,
            "timeout": timeout,
        },
        "selected_auto_parameters": response.get("auto_parameters"),
        "response_time": response.get("response_time"),
        "results": results,
        "external_content": True,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Search the web with Tavily.")
    parser.add_argument("query", help="Search query string")
    parser.add_argument("legacy_max_results", nargs="?", type=int, help=argparse.SUPPRESS)
    parser.add_argument(
        "--max-results",
        type=int,
        default=None,
        help=f"Maximum results to return (1-{MAX_RESULTS}, default: {DEFAULT_MAX_RESULTS})",
    )
    parser.add_argument(
        "--depth",
        choices=("basic", "advanced", "fast", "ultra-fast"),
        help="Explicit search depth. When omitted, Tavily may infer it.",
    )
    parser.add_argument(
        "--auto-parameters",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Let Tavily infer unspecified search parameters (default: enabled)",
    )
    parser.add_argument(
        "--topic",
        choices=("general", "news", "finance"),
        help="Optional Tavily search topic",
    )
    parser.add_argument(
        "--time-range",
        choices=("day", "week", "month", "year"),
        help="Only return recently published or updated results",
    )
    parser.add_argument(
        "--include-domain",
        action="append",
        dest="include_domains",
        help="Restrict search to a domain. Repeat for multiple domains.",
    )
    parser.add_argument(
        "--exclude-domain",
        action="append",
        dest="exclude_domains",
        help="Exclude a domain from search. Repeat for multiple domains.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=60,
        help=f"Provider timeout in seconds (>0 and <= {MAX_TIMEOUT_SECONDS}, default: 60)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    max_results = (
        args.max_results
        if args.max_results is not None
        else args.legacy_max_results
        if args.legacy_max_results is not None
        else DEFAULT_MAX_RESULTS
    )
    result = search(
        args.query,
        max_results=max_results,
        auto_parameters=args.auto_parameters,
        depth=args.depth,
        topic=args.topic,
        time_range=args.time_range,
        include_domains=args.include_domains,
        exclude_domains=args.exclude_domains,
        timeout=args.timeout,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
