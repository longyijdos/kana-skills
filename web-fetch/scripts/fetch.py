"""Fetch a public URL and return bounded, readable Markdown as JSON."""

import argparse
import ipaddress
import json
import os
import re
import socket
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlsplit


DEFAULT_MAX_BYTES = 5 * 1024 * 1024
DEFAULT_MAX_CHARS = 8_000
DEFAULT_TIMEOUT = 20.0
DEFAULT_CHUNKS_PER_SOURCE = 3
MAX_DOWNLOAD_BYTES = 20 * 1024 * 1024
MAX_OUTPUT_CHARS = 50_000
MIN_TIMEOUT = 1.0
MAX_TIMEOUT = 60.0
MIN_CHUNKS_PER_SOURCE = 1
MAX_CHUNKS_PER_SOURCE = 5
MAX_REDIRECTS = 5
MIN_USEFUL_HTML_CHARS = 200
REDIRECT_STATUSES = {301, 302, 303, 307, 308}
TEXT_CONTENT_TYPES = {
    "application/json",
    "application/ld+json",
    "application/xml",
    "application/xhtml+xml",
}
JS_SHELL_MARKERS = (
    "enable javascript",
    "javascript is required",
    "please turn javascript on",
    "checking your browser",
    "just a moment...",
)
JS_SHELL_MAX_CHARS = 2_000


class FetchFailure(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        retryable: bool = False,
        suggest_tavily: bool = False,
        status_code: int | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = retryable
        self.suggest_tavily = suggest_tavily
        self.status_code = status_code


def error_result(failure: FetchFailure) -> dict[str, Any]:
    error: dict[str, Any] = {
        "code": failure.code,
        "message": failure.message,
        "retryable": failure.retryable,
    }
    if failure.status_code is not None:
        error["status_code"] = failure.status_code
    if failure.suggest_tavily:
        error["suggested_engine"] = "tavily"
    return {"ok": False, "error": error}


def tavily_exception_retryable(exc: Exception) -> bool:
    error_name = type(exc).__name__
    if error_name in {
        "BadRequestError",
        "ForbiddenError",
        "InvalidAPIKeyError",
        "KeylessUnsupportedEndpointError",
        "MissingAPIKeyError",
        "TavilyKeylessLimitError",
        "UsageLimitExceededError",
    }:
        return False
    if error_name == "TimeoutError":
        return True

    message = str(exc).lower()
    return any(
        marker in message
        for marker in (
            "connection",
            "rate limit",
            "temporar",
            "timed out",
            "timeout",
            "429",
            "500",
            "502",
            "503",
            "504",
        )
    )


def validate_public_url(url: str) -> None:
    try:
        parsed = urlsplit(url)
        port = parsed.port
    except ValueError as exc:
        raise FetchFailure("invalid_url", f"Invalid URL: {exc}") from exc

    if parsed.scheme not in {"http", "https"}:
        raise FetchFailure("invalid_url", "URL must use http:// or https://")
    if parsed.username is not None or parsed.password is not None:
        raise FetchFailure("unsafe_url", "URLs containing credentials are not allowed")
    if not parsed.hostname:
        raise FetchFailure("invalid_url", "URL must include a hostname")

    hostname = parsed.hostname.rstrip(".").lower()
    if hostname == "localhost" or hostname.endswith(".localhost"):
        raise FetchFailure("unsafe_url", "Localhost URLs are not allowed")

    try:
        addresses = socket.getaddrinfo(
            hostname,
            port or (443 if parsed.scheme == "https" else 80),
            type=socket.SOCK_STREAM,
        )
    except socket.gaierror as exc:
        raise FetchFailure(
            "dns_failed",
            f"Could not resolve host {hostname}",
            retryable=True,
        ) from exc

    if not addresses:
        raise FetchFailure(
            "dns_failed",
            f"Host {hostname} did not resolve to an address",
            retryable=True,
        )

    for address in addresses:
        raw_ip = address[4][0].split("%", 1)[0]
        try:
            ip = ipaddress.ip_address(raw_ip)
        except ValueError as exc:
            raise FetchFailure(
                "unsafe_url",
                f"Host resolved to an invalid address: {raw_ip}",
            ) from exc
        if not ip.is_global:
            raise FetchFailure(
                "unsafe_url",
                f"Host resolves to a non-public address ({ip.compressed})",
            )


def decode_body(response: Any, body: bytes) -> str:
    response._content = body
    content_type = response.headers.get("Content-Type", "")
    if "charset=" not in content_type.lower():
        response.encoding = response.apparent_encoding or response.encoding or "utf-8"
    return response.text


def download(
    url: str,
    *,
    max_bytes: int,
    timeout: float,
) -> dict[str, Any]:
    try:
        import requests
    except ImportError as exc:
        raise FetchFailure(
            "missing_dependency",
            "requests is not installed. Run: python -m pip install -r requirements.txt",
        ) from exc

    headers = {
        "User-Agent": "WebFetch-Skill/1.0",
        "Accept": (
            "text/html,application/xhtml+xml,text/markdown,text/plain,"
            "application/json,application/xml;q=0.9,*/*;q=0.1"
        ),
    }
    current_url = url
    session = requests.Session()

    try:
        for redirect_count in range(MAX_REDIRECTS + 1):
            # Revalidate after every redirect so a public URL cannot bounce into a local service.
            validate_public_url(current_url)
            session.cookies.clear()
            try:
                response = session.get(
                    current_url,
                    headers=headers,
                    timeout=(min(timeout, 10.0), timeout),
                    allow_redirects=False,
                    stream=True,
                )
            except requests.exceptions.Timeout as exc:
                raise FetchFailure(
                    "timeout",
                    f"Request timed out for {current_url}",
                    retryable=True,
                    suggest_tavily=True,
                ) from exc
            except requests.exceptions.ConnectionError as exc:
                raise FetchFailure(
                    "connection_failed",
                    f"Failed to connect to {current_url}",
                    retryable=True,
                    suggest_tavily=True,
                ) from exc
            except requests.exceptions.RequestException as exc:
                raise FetchFailure(
                    "request_failed",
                    f"Request failed ({type(exc).__name__})",
                    retryable=True,
                    suggest_tavily=True,
                ) from exc

            if response.status_code in REDIRECT_STATUSES:
                location = response.headers.get("Location")
                response.close()
                if not location:
                    raise FetchFailure(
                        "invalid_redirect",
                        "Redirect response has no Location header",
                    )
                if redirect_count >= MAX_REDIRECTS:
                    raise FetchFailure("too_many_redirects", f"Exceeded {MAX_REDIRECTS} redirects")
                current_url = urljoin(current_url, location)
                continue

            if response.status_code >= 400:
                status_code = response.status_code
                response.close()
                suggest_tavily = status_code in {403, 408, 409, 425, 429} or status_code >= 500
                raise FetchFailure(
                    "http_error",
                    f"HTTP {status_code} for {current_url}",
                    retryable=status_code in {408, 409, 425, 429} or status_code >= 500,
                    suggest_tavily=suggest_tavily,
                    status_code=status_code,
                )

            content_type = response.headers.get("Content-Type", "")
            content_length_value = response.headers.get("Content-Length")
            try:
                content_length = int(content_length_value) if content_length_value else None
            except ValueError:
                content_length = None

            chunks: list[bytes] = []
            bytes_read = 0
            limited = False
            try:
                for chunk in response.iter_content(chunk_size=65_536):
                    if not chunk:
                        continue
                    remaining = max_bytes - bytes_read
                    if len(chunk) > remaining:
                        if remaining > 0:
                            chunks.append(chunk[:remaining])
                            bytes_read += remaining
                        limited = True
                        break
                    chunks.append(chunk)
                    bytes_read += len(chunk)
            except requests.exceptions.RequestException as exc:
                response.close()
                raise FetchFailure(
                    "body_read_failed",
                    f"Failed while reading the response body ({type(exc).__name__})",
                    retryable=True,
                    suggest_tavily=True,
                ) from exc

            body = b"".join(chunks)
            text = decode_body(response, body)
            final_url = response.url
            status_code = response.status_code
            response.close()
            return {
                "requested_url": url,
                "final_url": final_url,
                "status_code": status_code,
                "content_type": content_type,
                "content_length": content_length,
                "bytes_read": bytes_read,
                "limited": limited,
                "text": text,
            }
    finally:
        session.close()

    raise FetchFailure("request_failed", "Request ended without a response")


def clean_markdown(markdown: str) -> str:
    markdown = markdown.replace("\r\n", "\n").replace("\r", "\n")
    markdown = markdown.replace("\u200b", "").replace("\ufeff", "")
    markdown = "\n".join(line.rstrip() for line in markdown.splitlines())
    return re.sub(r"\n{4,}", "\n\n\n", markdown).strip()


def metadata_from_soup(soup: Any) -> dict[str, str | None]:
    def meta_value(*selectors: str) -> str | None:
        for selector in selectors:
            node = soup.select_one(selector)
            if node and node.get("content"):
                return str(node["content"]).strip()
        return None

    title = meta_value('meta[property="og:title"]', 'meta[name="twitter:title"]')
    if not title and soup.title:
        title = soup.title.get_text(" ", strip=True)
    return {
        "title": title,
        "author": meta_value('meta[name="author"]', 'meta[property="article:author"]'),
        "published_date": meta_value(
            'meta[property="article:published_time"]',
            'meta[name="date"]',
            'meta[name="datePublished"]',
        ),
    }


def markdownify_fallback(soup: Any, final_url: str) -> str:
    try:
        from markdownify import markdownify
    except ImportError as exc:
        raise FetchFailure(
            "missing_dependency",
            "markdownify is not installed. Run: python -m pip install -r requirements.txt",
        ) from exc

    discarded_tags = [
        "script",
        "style",
        "nav",
        "footer",
        "header",
        "noscript",
        "iframe",
        "form",
        "button",
        "svg",
    ]
    for tag in soup(discarded_tags):
        tag.decompose()
    root = soup.find("article") or soup.find("main") or soup.find(role="main") or soup.body or soup
    for link in root.select("a[href]"):
        link["href"] = urljoin(final_url, link["href"])
    return markdownify(
        str(root),
        heading_style="ATX",
        bullets="-",
        autolinks=True,
        default_title=False,
        table_infer_header=True,
    )


def extract_html(html: str, final_url: str) -> dict[str, Any]:
    try:
        from bs4 import BeautifulSoup
        from trafilatura import extract
        from trafilatura.metadata import extract_metadata
    except ImportError as exc:
        raise FetchFailure(
            "missing_dependency",
            "HTML extraction dependencies are missing. "
            "Run: python -m pip install -r requirements.txt",
        ) from exc

    soup = BeautifulSoup(html, "html.parser")
    metadata = metadata_from_soup(soup)
    try:
        extracted_metadata = extract_metadata(html, default_url=final_url)
        if extracted_metadata:
            values = extracted_metadata.as_dict()
            metadata = {
                "title": values.get("title") or metadata["title"],
                "author": values.get("author") or metadata["author"],
                "published_date": values.get("date") or metadata["published_date"],
            }
    except Exception:
        # Metadata is helpful but must never make otherwise readable content fail.
        pass

    has_semantic_root = bool(soup.find("article") or soup.find("main") or soup.find(role="main"))
    structured = clean_markdown(markdownify_fallback(soup, final_url))
    if has_semantic_root and len(structured) >= MIN_USEFUL_HTML_CHARS:
        return {**metadata, "content": structured, "extraction_method": "markdownify-semantic"}

    primary = extract(
        html,
        url=final_url,
        output_format="markdown",
        include_comments=False,
        include_tables=True,
        include_links=True,
        include_images=False,
        deduplicate=True,
    )
    primary = clean_markdown(primary or "")
    if len(primary) >= MIN_USEFUL_HTML_CHARS:
        return {**metadata, "content": primary, "extraction_method": "trafilatura"}

    if not structured:
        raise FetchFailure(
            "extraction_failed",
            "The page was fetched but no readable HTML content could be extracted",
            suggest_tavily=True,
        )
    return {**metadata, "content": structured, "extraction_method": "markdownify-fallback"}


def local_fetch(url: str, *, max_bytes: int, timeout: float) -> dict[str, Any]:
    downloaded = download(url, max_bytes=max_bytes, timeout=timeout)
    media_type = downloaded["content_type"].split(";", 1)[0].strip().lower()

    if media_type in {"text/html", "application/xhtml+xml", ""}:
        extracted = extract_html(downloaded["text"], downloaded["final_url"])
    elif media_type.startswith("text/") or media_type in TEXT_CONTENT_TYPES:
        extracted = {
            "title": None,
            "author": None,
            "published_date": None,
            "content": clean_markdown(downloaded["text"]),
            "extraction_method": "direct-text",
        }
    else:
        raise FetchFailure(
            "unsupported_content_type",
            f"Unsupported content type: {media_type or 'unknown'}",
        )

    content = extracted["content"]
    if not content:
        raise FetchFailure(
            "empty_content",
            "The response contained no readable text",
            suggest_tavily=True,
        )
    return {
        "ok": True,
        "engine": "local",
        "requested_url": downloaded["requested_url"],
        "final_url": downloaded["final_url"],
        "title": extracted["title"],
        "author": extracted["author"],
        "published_date": extracted["published_date"],
        "status_code": downloaded["status_code"],
        "content_type": downloaded["content_type"],
        "content_length": downloaded["content_length"],
        "bytes_read": downloaded["bytes_read"],
        "limited": downloaded["limited"],
        "format": (
            "markdown"
            if media_type in {"text/html", "application/xhtml+xml", ""}
            else "text"
        ),
        "extraction_method": extracted["extraction_method"],
        "_source_chars": len(downloaded["text"]),
        "_content": content,
    }


def tavily_fetch(
    url: str,
    *,
    extract_depth: str,
    query: str | None,
    chunks_per_source: int,
    timeout: float,
) -> dict[str, Any]:
    validate_public_url(url)
    api_key = os.environ.get("TAVILY_API_KEY")
    if not api_key:
        raise FetchFailure(
            "missing_api_key",
            "TAVILY_API_KEY is required for the Tavily extraction engine",
        )
    try:
        from tavily import TavilyClient
    except ImportError as exc:
        raise FetchFailure(
            "missing_dependency",
            "tavily-python is not installed. Run: python -m pip install -r requirements.txt",
        ) from exc

    kwargs: dict[str, Any] = {
        "urls": url,
        "extract_depth": extract_depth,
        "format": "markdown",
        "include_usage": True,
        "timeout": timeout,
    }
    if query:
        kwargs["query"] = query
        kwargs["chunks_per_source"] = chunks_per_source
    try:
        with TavilyClient(api_key=api_key) as client:
            response = client.extract(**kwargs)
    except Exception as exc:  # Provider exceptions vary across SDK releases.
        message = str(exc).replace(api_key, "[REDACTED]")
        raise FetchFailure(
            "tavily_extract_failed",
            f"Tavily extraction failed ({type(exc).__name__}): {message}",
            retryable=tavily_exception_retryable(exc),
        ) from exc

    results = response.get("results", [])
    if not results:
        failed = response.get("failed_results", [])
        detail = failed[0].get("error") if failed and isinstance(failed[0], dict) else None
        raise FetchFailure(
            "tavily_extract_failed",
            f"Tavily returned no extracted content{f': {detail}' if detail else ''}",
            retryable=True,
        )

    item = results[0]
    content = clean_markdown(item.get("raw_content") or "")
    if not content:
        raise FetchFailure("empty_content", "Tavily returned an empty extraction", retryable=True)
    title = item.get("title")
    if not title:
        first_line = content.splitlines()[0].lstrip("# ").strip() if content else ""
        title = first_line or None
    return {
        "ok": True,
        "engine": "tavily",
        "requested_url": url,
        "final_url": item.get("url") or url,
        "title": title,
        "author": None,
        "published_date": None,
        "status_code": None,
        "content_type": "text/markdown",
        "content_length": None,
        "bytes_read": None,
        "limited": False,
        "format": "markdown",
        "extraction_method": f"tavily-{extract_depth}",
        "query": query,
        "query_applied": bool(query),
        "chunks_per_source": chunks_per_source if query else None,
        "request_id": response.get("request_id"),
        "response_time": response.get("response_time"),
        "usage": response.get("usage"),
        "_content": content,
    }


def tavily_suggestion_reason(result: dict[str, Any]) -> str | None:
    if result.get("format") != "markdown":
        return None
    content = result.get("_content", "")
    normalized = content.lower()
    source_chars = result.get("_source_chars", 0)
    if len(content) < MIN_USEFUL_HTML_CHARS and source_chars > 2_000:
        return "local extraction was too short"
    if len(content) <= JS_SHELL_MAX_CHARS and any(
        marker in normalized for marker in JS_SHELL_MARKERS
    ):
        return "page appears to require JavaScript"
    return None


def save_content(content: str, output_path: str) -> str:
    destination = Path(output_path).expanduser()
    if not destination.parent.is_dir():
        raise FetchFailure(
            "save_directory_missing",
            f"Save directory does not exist: {destination.parent}",
        )

    created = False
    try:
        with destination.open("x", encoding="utf-8", newline="\n") as output:
            created = True
            output.write(content)
    except FileExistsError as exc:
        raise FetchFailure(
            "save_path_exists",
            f"Refusing to overwrite existing file: {destination}",
        ) from exc
    except OSError as exc:
        if created:
            try:
                destination.unlink()
            except OSError:
                pass
        raise FetchFailure(
            "save_failed",
            f"Could not save extracted content ({type(exc).__name__}): {exc}",
        ) from exc
    return str(destination.resolve())


def finalize_result(
    result: dict[str, Any],
    *,
    max_chars: int,
    save_path: str | None,
) -> dict[str, Any]:
    content = result.pop("_content")
    result.pop("_source_chars", None)
    content_chars = len(content)
    end = min(content_chars, max_chars)
    if end < content_chars:
        # Prefer a paragraph boundary while keeping a useful preview.
        boundary = content.rfind("\n\n", max_chars // 2, end)
        if boundary > 0:
            end = boundary
    preview = content[:end].strip()
    result.update(
        {
            "content": preview,
            "content_chars": content_chars,
            "truncated": end < content_chars,
            "external_content": True,
        }
    )
    if save_path:
        result["saved_to"] = save_content(content, save_path)
        result["saved_chars"] = content_chars
    return result


def fetch(
    url: str,
    *,
    engine: str,
    extract_depth: str,
    query: str | None,
    chunks_per_source: int,
    max_chars: int,
    max_bytes: int,
    save_path: str | None,
    timeout: float,
) -> dict[str, Any]:
    if engine not in {"local", "tavily"}:
        raise FetchFailure("invalid_engine", "engine must be local or tavily")
    if extract_depth not in {"basic", "advanced"}:
        raise FetchFailure(
            "invalid_extract_depth",
            "extract_depth must be basic or advanced",
        )
    if not 1 <= max_chars <= MAX_OUTPUT_CHARS:
        raise FetchFailure(
            "invalid_max_chars",
            f"max_chars must be between 1 and {MAX_OUTPUT_CHARS}",
        )
    if not 1 <= max_bytes <= MAX_DOWNLOAD_BYTES:
        raise FetchFailure(
            "invalid_max_bytes",
            f"max_bytes must be between 1 and {MAX_DOWNLOAD_BYTES}",
        )
    if not MIN_TIMEOUT <= timeout <= MAX_TIMEOUT:
        raise FetchFailure(
            "invalid_timeout",
            f"timeout must be between {MIN_TIMEOUT:g} and {MAX_TIMEOUT:g} seconds",
        )
    if not MIN_CHUNKS_PER_SOURCE <= chunks_per_source <= MAX_CHUNKS_PER_SOURCE:
        raise FetchFailure(
            "invalid_chunks_per_source",
            "chunks_per_source must be between "
            f"{MIN_CHUNKS_PER_SOURCE} and {MAX_CHUNKS_PER_SOURCE}",
        )

    query = query.strip() if query else None
    if query and engine != "tavily":
        raise FetchFailure(
            "query_requires_tavily",
            "--query requires --engine tavily",
        )
    validate_public_url(url)

    if engine == "tavily":
        try:
            return finalize_result(
                tavily_fetch(
                    url,
                    extract_depth=extract_depth,
                    query=query,
                    chunks_per_source=chunks_per_source,
                    timeout=timeout,
                ),
                max_chars=max_chars,
                save_path=save_path,
            )
        except FetchFailure as failure:
            return error_result(failure)

    try:
        local_result = local_fetch(url, max_bytes=max_bytes, timeout=timeout)
    except FetchFailure as failure:
        return error_result(failure)

    reason = tavily_suggestion_reason(local_result)
    if reason:
        return error_result(
            FetchFailure(
                "local_extraction_insufficient",
                reason,
                suggest_tavily=True,
            )
        )
    return finalize_result(local_result, max_chars=max_chars, save_path=save_path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch a public URL as readable Markdown.")
    parser.add_argument("url", help="Public HTTP or HTTPS URL")
    parser.add_argument("legacy_max_chars", nargs="?", type=int, help=argparse.SUPPRESS)
    parser.add_argument(
        "--engine",
        choices=("local", "tavily"),
        default="local",
        help="Use local extraction or Tavily (default: local)",
    )
    parser.add_argument(
        "--extract-depth",
        choices=("basic", "advanced"),
        default="basic",
        help="Tavily extraction depth when that engine is used (default: basic)",
    )
    parser.add_argument(
        "--query",
        help="Return Tavily chunks relevant to this question; requires --engine tavily",
    )
    parser.add_argument(
        "--chunks-per-source",
        type=int,
        default=DEFAULT_CHUNKS_PER_SOURCE,
        help="Relevant Tavily chunks when --query is used (1-5; default: 3)",
    )
    parser.add_argument(
        "--max-chars",
        type=int,
        default=None,
        help=f"Maximum returned characters (1-{MAX_OUTPUT_CHARS}; default: {DEFAULT_MAX_CHARS})",
    )
    parser.add_argument(
        "--max-bytes",
        type=int,
        default=DEFAULT_MAX_BYTES,
        help=(
            "Maximum downloaded bytes for local extraction "
            f"(1-{MAX_DOWNLOAD_BYTES}; default: {DEFAULT_MAX_BYTES})"
        ),
    )
    parser.add_argument(
        "--save",
        metavar="PATH",
        help="Save the complete extracted Markdown or text; refuses to overwrite",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT,
        help=(
            f"Request timeout in seconds ({MIN_TIMEOUT:g}-{MAX_TIMEOUT:g}; "
            f"default: {DEFAULT_TIMEOUT:g})"
        ),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    max_chars = (
        args.max_chars
        if args.max_chars is not None
        else args.legacy_max_chars
        if args.legacy_max_chars is not None
        else DEFAULT_MAX_CHARS
    )
    try:
        result = fetch(
            args.url,
            engine=args.engine,
            extract_depth=args.extract_depth,
            query=args.query,
            chunks_per_source=args.chunks_per_source,
            max_chars=max_chars,
            max_bytes=args.max_bytes,
            save_path=args.save,
            timeout=args.timeout,
        )
    except FetchFailure as failure:
        result = error_result(failure)

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
