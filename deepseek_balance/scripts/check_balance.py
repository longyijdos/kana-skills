"""
kana-skills: deepseek_balance
Query DeepSeek API account balance.
"""
import sys
import os
import json
import urllib.request
import urllib.error


DEEPSEEK_BALANCE_URL = "https://api.deepseek.com/user/balance"


def check_balance() -> dict:
    """Query DeepSeek API for account balance."""
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        return {"error": "DEEPSEEK_API_KEY environment variable not set"}

    req = urllib.request.Request(
        DEEPSEEK_BALANCE_URL,
        method="GET",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = resp.read().decode("utf-8")
            data = json.loads(body)
            return {
                "status_code": resp.status,
                **data,
            }
    except urllib.error.HTTPError as e:
        try:
            detail = json.loads(e.read().decode("utf-8"))
        except Exception:
            detail = e.reason
        return {
            "error": f"HTTP {e.code}: {detail}",
            "status_code": e.code,
        }
    except urllib.error.URLError as e:
        return {"error": f"Connection failed: {e.reason}"}
    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    result = check_balance()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if "error" in result:
        sys.exit(1)
