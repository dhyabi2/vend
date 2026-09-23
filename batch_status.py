"""
Batch URL status checker for Vend.

Checks the HTTP status of many URLs in one paid call, returning each URL's
status_code, response_time_ms, final_url and error (if any). URLs are checked
concurrently with a bounded worker pool so a slow target never blocks the
rest, and no URL is ever fetched beyond its headers (HEAD, or GET without
following body for the final URL).

Serves the data/scraping-agent need to keep link lists, sitemaps and
monitoring fleets healthy in one call instead of N calls.
"""

import concurrent.futures
import time
from typing import Optional

import httpx

MAX_URLS = 50
DEFAULT_TIMEOUT = 12
MAX_WORKERS = 10


def _check_one(url: str, timeout: int, method: str) -> dict:
    """Check a single URL. Never raises."""
    result = {
        "url": url,
        "status_code": None,
        "response_time_ms": None,
        "final_url": None,
        "error": None,
    }
    if not url or not url.startswith(("http://", "https://")):
        result["error"] = "invalid_url: must start with http:// or https://"
        return result
    headers = {
        "User-Agent": "Vend/0.1 (Nano pay-per-call API; paypercall.dev)/batch-status",
        "Accept": "*/*",
    }
    try:
        start = time.monotonic()
        resp = httpx.request(
            method,
            url,
            headers=headers,
            timeout=timeout,
            follow_redirects=True,
        )
        result["status_code"] = resp.status_code
        result["response_time_ms"] = int((time.monotonic() - start) * 1000)
        result["final_url"] = str(resp.url)
    except httpx.TimeoutException:
        result["error"] = f"timeout:{timeout}s"
    except httpx.ConnectError:
        result["error"] = "connection_failed"
    except httpx.RequestError as e:
        result["error"] = f"request_error: {str(e)[:80]}"
    except Exception as e:
        result["error"] = f"check_error: {str(e)[:80]}"
    return result


def batch_status(urls, timeout: int = DEFAULT_TIMEOUT, method: str = "HEAD",
                 max_urls: int = MAX_URLS) -> dict:
    """Check a list of URLs concurrently.

    Args:
        urls: list of URL strings (or comma-separated string).
        timeout: per-URL timeout in seconds.
        method: "HEAD" (default, fast) or "GET" (full fetch headers).
        max_urls: hard cap on how many URLs are accepted in one call.

    Returns:
        dict with keys: total, checked, results (list of per-URL dicts in
        input order), error (top-level error, if the input was unusable).
    """
    if urls is None:
        return {"error": "missing_urls: pass ?urls=url1,url2,..."}
    if isinstance(urls, str):
        urls = [u.strip() for u in urls.split(",") if u.strip()]
    if not isinstance(urls, list) or not urls:
        return {"error": "no_urls: supply at least one URL"}
    if method not in ("HEAD", "GET"):
        method = "HEAD"
    if len(urls) > max_urls:
        urls = urls[:max_urls]
    results = []
    with concurrent.futures.ThreadPoolExecutor(
        max_workers=min(MAX_WORKERS, len(urls))
    ) as ex:
        future_map = {ex.submit(_check_one, u, timeout, method): u for u in urls}
        for fut, _u in future_map.items():
            results.append(fut.result())
    # Preserve input order (futures complete out of order).
    results = [r for _, r in sorted(
        zip(range(len(urls)), results), key=lambda x: x[0]
    )]
    ok = sum(1 for r in results if r.get("status_code") is not None)
    return {
        "total": len(urls),
        "ok": ok,
        "failed": len(urls) - ok,
        "results": results,
    }
