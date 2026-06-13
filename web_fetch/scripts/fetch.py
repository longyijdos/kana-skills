"""
kana-skills: web_fetch
Fetch a URL and extract readable text content.
"""
import sys
import json
import re

def fetch(url: str, max_chars: int = 8000):
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
        resp = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
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

    # Only parse HTML
    if "text/html" not in content_type and "application/xhtml" not in content_type:
        return {
            "url": url,
            "title": None,
            "text": resp.text[:max_chars] if len(resp.text) <= max_chars else resp.text[:max_chars] + "...",
            "status_code": resp.status_code,
            "content_type": content_type,
            "truncated": len(resp.text) > max_chars,
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

    return {
        "url": url,
        "title": title,
        "text": text,
        "status_code": resp.status_code,
        "content_type": content_type,
        "truncated": truncated,
    }

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: python fetch.py <url> [max_chars]"}, ensure_ascii=False))
        sys.exit(1)

    url = sys.argv[1]
    max_chars = int(sys.argv[2]) if len(sys.argv) > 2 else 8000
    result = fetch(url, max_chars)
    print(json.dumps(result, ensure_ascii=False, indent=2))
