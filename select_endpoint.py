"""
CSS-selector structured extraction for Vend.

Fetches a public URL and returns the text (or a chosen attribute) of the
elements matching a CSS selector -- so a data/scraping agent can pull the
structured fields it cares about (prices, headings, table rows, link hrefs)
in one paid call instead of scraping the whole page and re-parsing it.

Rules that make a stranger's call worth paying for (laws L61-L62):
- A valid URL + selector returns the matching elements' text/attr, capped.
- A malformed selector or un-fetchable URL refuses politely, never charges.
Only public content is ever returned; no login, no cookies, no buyer data.
"""

import re
from typing import Optional

import httpx
import lxml.html

DEFAULT_TIMEOUT = 15
DEFAULT_LIMIT = 50
MAX_LIMIT = 200
MAX_TEXT_CHARS = 4000


def _collapse(html):
    """lxml.html.fromstring needs HTML with features; parse as HTML."""
    return lxml.html.document_fromstring(html)


def select_from_url(url: str, selector: str, attr: Optional[str] = None,
                    limit: int = DEFAULT_LIMIT, timeout: int = DEFAULT_TIMEOUT) -> dict:
    """Fetch `url`, parse it, and return the text/attr of elements matching `selector`.

    Never raises. Returns a dict with keys: url, selector, attr, count,
    trimmed, title, matches (list of dicts), error (on any failure).
    """
    result = {
        "url": url,
        "selector": selector,
        "attr": attr,
        "count": 0,
        "trimmed": False,
        "title": "",
        "matches": [],
        "error": None,
    }

    # --- Validate input first: refuse politely, never charge on a bad call.
    if not url or not url.startswith(("http://", "https://")):
        result["error"] = "invalid_url: must start with http:// or https://"
        return result
    if not selector or not isinstance(selector, str) or not selector.strip():
        result["error"] = "missing_selector: pass ?selector= (e.g. h1, .price, table tr)"
        return result
    if not isinstance(limit, int) or limit < 1:
        limit = DEFAULT_LIMIT
    limit = min(limit, MAX_LIMIT)

    # --- Fetch
    headers = {
        "User-Agent": "Vend/0.1 (Nano pay-per-call API; paypercall.dev)/select",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
    try:
        resp = httpx.get(url, headers=headers, timeout=timeout, follow_redirects=True)
    except httpx.TimeoutException:
        result["error"] = f"timeout fetching {url} (limit: {timeout}s)"
        return result
    except httpx.RequestError as e:
        result["error"] = f"request_failed: {str(e)[:100]}"
        return result

    if resp.status_code != 200:
        result["error"] = f"http_{resp.status_code} fetching {url}"
        return result
    html = resp.text
    if not html or len(html) < 50:
        result["error"] = "empty_or_too_small_response"
        return result

    # --- Parse
    try:
        doc = _collapse(html)
        title_el = doc.find(".//title")
        if title_el is not None and title_el.text:
            result["title"] = title_el.text.strip()
    except Exception as e:
        result["error"] = f"parse_error: {str(e)[:100]}"
        return result

    try:
        nodes = doc.cssselect(selector)
    except Exception as e:
        result["error"] = f"invalid_selector: {str(e)[:100]}"
        return result

    trimmed = len(nodes) > limit
    nodes = nodes[:limit]
    matches = []
    for i, node in enumerate(nodes):
        entry = {"index": i}
        if attr:
            val = node.get(attr)
            if val is None:
                # allow data-* and aria-* attributes; direct get covers them
                val = node.get(attr)
            entry["value"] = val if val is not None else None
        else:
            text = " ".join((node.text_content() or "").split())
            text = text[:MAX_TEXT_CHARS]
            entry["text"] = text
        matches.append(entry)

    result["count"] = len(matches)
    result["trimmed"] = trimmed
    result["matches"] = matches
    return result
