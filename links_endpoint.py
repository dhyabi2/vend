"""
Link extraction for Vend.

Fetches a public URL and returns every anchor/main link found on the page with
its href, visible text, and a small set of computed metadata (absolute URL,
external vs same-site, target, rel) -- so a data/scraping/research agent can
crawl a site, audit outbound links, or build a sitemap in one paid call instead
of fetching and re-parsing the whole page.

Rules that make a stranger's call worth paying for (laws L67-L68):
- A valid URL returns the page's links as structured JSON, capped and trimmed.
- A malformed URL or un-fetchable page refuses politely, never charges.
- Only public page content is returned; no login, no cookies, no buyer data.
"""

from typing import Optional
from urllib.parse import urljoin, urlparse

import httpx
import lxml.html

DEFAULT_TIMEOUT = 15
DEFAULT_LIMIT = 200
MAX_LIMIT = 1000
MAX_TEXT_CHARS = 300
MAX_HREF_CHARS = 2000


def _is_external(href: str, base_host: str) -> bool:
    """True when `href` points at a different host than the page (or is opaque)."""
    if not href:
        return False
    try:
        p = urlparse(href)
    except ValueError:
        return False
    if p.scheme not in ("http", "https", ""):
        return True  # mailto:, tel:, data:, javascript: are not web-same-site
    if not p.netloc:
        return False  # relative path or fragment -> same site
    return p.netloc.lower() != base_host.lower()


def links_from_url(url: str, limit: int = DEFAULT_LIMIT,
                   timeout: int = DEFAULT_TIMEOUT) -> dict:
    """Fetch `url`, parse it, and return the page's links with metadata.

    Never raises. Returns a dict with keys: url, count, trimmed, title,
    links (list of dicts: href, text, absolute, external, target, rel),
    error (on any failure).
    """
    result = {
        "url": url,
        "count": 0,
        "trimmed": False,
        "title": "",
        "links": [],
        "error": None,
    }

    # --- Validate input first: refuse politely, never charge on a bad call.
    if not isinstance(url, str) or not url or not url.startswith(("http://", "https://")):
        result["error"] = "invalid_url: must start with http:// or https://"
        return result
    if not isinstance(limit, int) or limit < 1:
        limit = DEFAULT_LIMIT
    limit = min(limit, MAX_LIMIT)

    # --- Fetch
    headers = {
        "User-Agent": "Vend/0.1 (Nano pay-per-call API; paypercall.dev)/links",
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
        doc = lxml.html.document_fromstring(html)
        title_el = doc.find(".//title")
        if title_el is not None and title_el.text:
            result["title"] = title_el.text.strip()
    except Exception as e:
        result["error"] = f"parse_error: {str(e)[:100]}"
        return result

    # --- Collect anchor links
    try:
        anchors = doc.cssselect("a[href]")
    except Exception as e:
        result["error"] = f"parse_error: {str(e)[:100]}"
        return result

    base_host = urlparse(url).netloc
    seen = set()
    links = []
    for a in anchors:
        raw = a.get("href") or ""
        raw = raw.strip()
        if not raw:
            continue
        if len(raw) > MAX_HREF_CHARS:
            raw = raw[:MAX_HREF_CHARS]
        text = " ".join((a.text_content() or "").split())
        text = text[:MAX_TEXT_CHARS]
        absolute = urljoin(url, raw)
        entry = {
            "text": text,
            "href": raw,
            "absolute": absolute,
            "external": _is_external(raw, base_host),
            "target": a.get("target"),
            "rel": a.get("rel"),
        }
        # Dedupe by absolute URL + text to keep results lean like a crawl map.
        dedup_key = (absolute, text)
        if dedup_key in seen:
            continue
        seen.add(dedup_key)
        links.append(entry)

    trimmed = len(links) > limit
    result["links"] = links[:limit]
    result["count"] = len(result["links"])
    result["trimmed"] = trimmed
    return result
