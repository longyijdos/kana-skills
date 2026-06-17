"""
kana-skills: web-fetch
Fetch a URL and extract readable text content.
"""
import json
import re
import argparse

DEFAULT_MAX_BYTES = 5 * 1024 * 1024


def fetch(url: str, max_chars: int = 8000, max_bytes: int = DEFAULT_MAX_BYTES):
    """Fetch URL and return structured content."""
    # Validate URL
    if not url.startswith(("http://", "https://")):
        return {"error": f"Invalid URL: {url}. Must start with http:// or https://"}

    try:
        import requests
    except ImportError:
        return {"error": "requests not installed. Run: pip install requests"}

    try:
        from bs4 import BeautifulSoup
    except ImportError:
        return {"error": "beautifulsoup4 not installed. Run: pip install beautifulsoup4"}

    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }
        resp = requests.get(url, headers=headers, timeout=15, allow_redirects=True, stream=True)
        resp.raise_for_status()
    except requests.exceptions.Timeout:
        return {"error": f"Request timed out for {url}"}
    except requests.exceptions.ConnectionError:
        return {"error": f"Failed to connect to {url}"}
    except requests.exceptions.HTTPError as e:
        return {"error": f"HTTP error: {e.response.status_code} for {url}"}
    except requests.exceptions.RequestException as e:
        return {"error": f"Request failed: {str(e)}"}

    content_type = resp.headers.get("Content-Type", "")
    content_length = resp.headers.get("Content-Length")
    try:
        content_length = int(content_length) if content_length is not None else None
    except ValueError:
        content_length = None

    chunks = []
    bytes_read = 0
    limited = False
    try:
        for chunk in resp.iter_content(chunk_size=65536):
            if not chunk:
                continue
            if bytes_read + len(chunk) > max_bytes:
                chunks.append(chunk[: max_bytes - bytes_read])
                bytes_read = max_bytes
                limited = True
                break
            chunks.append(chunk)
            bytes_read += len(chunk)
    except requests.exceptions.RequestException as e:
        return {"error": f"Failed reading response body: {str(e)}"}

    resp._content = b"".join(chunks)
    resp.encoding = resp.encoding or resp.apparent_encoding

    # Only parse HTML
    if "text/html" not in content_type and "application/xhtml" not in content_type:
        text = resp.text
        return {
            "url": url,
            "final_url": resp.url,
            "title": None,
            "text": text[:max_chars] if len(text) <= max_chars else text[:max_chars] + "...",
            "status_code": resp.status_code,
            "content_type": content_type,
            "content_length": content_length,
            "bytes_read": bytes_read,
            "limited": limited,
            "truncated": len(text) > max_chars or limited,
        }

    soup = BeautifulSoup(resp.text, "html.parser")

    # Remove non-content elements
    for tag in soup(["script", "style", "nav", "footer", "header", "noscript", "iframe"]):
        tag.decompose()

    title = None
    if soup.title:
        title = soup.title.get_text(strip=True)

    # Try to extract main content first
    main = soup.find("main") or soup.find("article") or soup.find(role="main")
    if main:
        text = main.get_text(separator="\n", strip=True)
    else:
        text = soup.body.get_text(separator="\n", strip=True) if soup.body else soup.get_text(separator="\n", strip=True)

    # Collapse whitespace
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)

    truncated = len(text) > max_chars
    if truncated:
        text = text[:max_chars] + "..."
    truncated = truncated or limited

    return {
        "url": url,
        "final_url": resp.url,
        "title": title,
        "text": text,
        "status_code": resp.status_code,
        "content_type": content_type,
        "content_length": content_length,
        "bytes_read": bytes_read,
        "limited": limited,
        "truncated": truncated,
    }

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch a URL and extract readable text.")
    parser.add_argument("url", help="URL to fetch")
    parser.add_argument("legacy_max_chars", nargs="?", type=int, help=argparse.SUPPRESS)
    parser.add_argument("--max-chars", type=int, default=None, help="Maximum characters to return")
    parser.add_argument("--max-bytes", type=int, default=DEFAULT_MAX_BYTES, help="Maximum response bytes to read")
    args = parser.parse_args()

    if args.max_chars is not None:
        max_chars = args.max_chars
    elif args.legacy_max_chars is not None:
        max_chars = args.legacy_max_chars
    else:
        max_chars = 8000
    if max_chars < 1:
        print(json.dumps({"error": "max_chars must be at least 1"}, ensure_ascii=False, indent=2))
        raise SystemExit(1)
    if args.max_bytes < 1:
        print(json.dumps({"error": "max_bytes must be at least 1"}, ensure_ascii=False, indent=2))
        raise SystemExit(1)

    result = fetch(args.url, max_chars, args.max_bytes)
    print(json.dumps(result, ensure_ascii=False, indent=2))
