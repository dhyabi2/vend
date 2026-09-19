"""
HTTP Link Status Checker for Vend.

Checks if a URL is reachable and returns:
  - status_code, response_time_ms, final_url, redirect_chain
  - content_type, content_length
  - error on failure

Uses httpx (already a dependency for extract.py).
"""

import time
from typing import Optional
import httpx


def check_link(url: str, timeout: int = 10) -> dict:
    """
    Check the HTTP status of a URL.

    Args:
        url: The URL to check
        timeout: HTTP request timeout in seconds

    Returns:
        dict with keys: url, status_code, response_time_ms, final_url,
                        redirect_chain, content_type, content_length, error
    """
    result = {
        "url": url,
        "status_code": None,
        "response_time_ms": None,
        "final_url": None,
        "redirect_chain": [],
        "content_type": None,
        "content_length": None,
        "error": None,
    }

    # Validate URL
    if not url or not url.startswith(("http://", "https://")):
        result["error"] = "Invalid URL: must start with http:// or https://"
        return result

    try:
        headers = {
            "User-Agent": "Vend/0.1 (Nano pay-per-call API; paypercall.dev)/link-check",
            "Accept": "*/*",
        }

        start = time.monotonic()
        resp = httpx.get(
            url,
            headers=headers,
            timeout=timeout,
            follow_redirects=True,
        )
        elapsed_ms = int((time.monotonic() - start) * 1000)

        # Redirect chain: reconstruct from history
        chain = []
        for r in resp.history:
            chain.append({
                "url": str(r.url),
                "status_code": r.status_code,
            })

        result["status_code"] = resp.status_code
        result["response_time_ms"] = elapsed_ms
        result["final_url"] = str(resp.url)
        result["redirect_chain"] = chain
        result["content_type"] = resp.headers.get("content-type")
        result["content_length"] = resp.headers.get("content-length")

    except httpx.TimeoutException:
        result["error"] = f"Timeout checking {url} (limit: {timeout}s)"
    except httpx.ConnectError:
        result["error"] = f"Connection failed: {url}"
    except httpx.RequestError as e:
        result["error"] = f"Request failed: {str(e)[:100]}"
    except Exception as e:
        result["error"] = f"Check error: {str(e)[:100]}"

    return result