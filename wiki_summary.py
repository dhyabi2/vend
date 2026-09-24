"""
Wikipedia entity summary for Vend.

Wraps the free, keyless, highly-reliable English Wikipedia REST Summary API
into a clean, bounded JSON endpoint. Agents use it for research, lead-gen and
entity lookups: give a company, person, technology or topic and get a distilled
profile — title, one-paragraph extract, normalized description, thumbnail,
confidence hints and a canonical URL — without scraping or parsing HTML.

Pairs naturally with Vend's web-search (find sources) and extract (read a page):
/wiki-summary answers "what is this thing, in one clean paragraph".

Uses httpx (a project dependency) for the HTTP client (Wikipedia's anti-bot
layer rate-limits urllib's TLS fingerprint with 403; httpx/curl pass). Free,
keyless upstream (same request budget as the public site; concurrency-friendly).
Priced at 0.0001 XNO per call.

Upstream reliability: the en.wikipedia REST endpoint is a stable service that
returns 200 in well under 200 ms in normal operation; a non-200 is treated as
an error (never a fabricated empty summary) so a buyer is never charged for an
unverifiable answer.
"""

import json
import time
import urllib.request

_WIKI = "https://en.wikipedia.org/api/rest_v1/page/summary"
_MAX_BYTES = 2 * 1024 * 1024  # 2 MiB
_UA = "Vend/0.1 (Nano pay-per-call API; paypercall.dev)"
# Any value the caller may put in a URL path segment that we must neutralise.
_SAFE_TITLE = str.maketrans({" ": "_", "\n": "_", "\t": "_", "/": "_", "\\": "_"})


def _get_json(url: str, timeout: int = 15) -> dict:
    # Use httpx (a project dependency) rather than urllib: Wikipedia's anti-bot
    # layer fingerprints urllib's TLS handshake and rate-limits it with 403 even
    # for genuine 404 titles, while httpx/curl pass. Verified on 2026-09-23:
    # urllib -> 403, httpx/curl -> 200/404 for the same URL + UA.
    import httpx

    headers = {"User-Agent": _UA, "Accept": "application/json"}
    for attempt in (1, 2):
        try:
            resp = httpx.get(url, headers=headers, timeout=timeout, follow_redirects=True)
            if resp.status_code == 404:
                raise urllib.error.HTTPError(url, 404, "Not Found", None, None)
            if resp.status_code in (403, 429, 500, 502, 503, 504) and attempt == 1:
                time.sleep(1.0)
                continue
            resp.raise_for_status()
            if len(resp.content) > _MAX_BYTES:
                raise ValueError("Upstream response exceeds size limit")
            return resp.json()
        except httpx.HTTPStatusError as e:
            if attempt == 1 and e.response.status_code in (403, 429, 500, 502, 503, 504):
                time.sleep(1.0)
                continue
            raise urllib.error.HTTPError(
                url, e.response.status_code, e.response.reason_phrase, None, None
            )


def wiki_summary(query: str, lang: str = "en", timeout: int = 15) -> dict:
    """Return a clean Wikipedia summary profile for a topic.

    Args:
        query: the entity / topic to look up (free text; the API resolves it).
        lang: two-letter Wikipedia language code (default 'en').
        timeout: HTTP timeout in seconds.

    Returns:
        dict with keys: found (bool), title, description, extract (one-paragraph
        summary), thumbnail, originalimage, wikidata_id, lang, url, errors.
        If the topic has no page, found=False with a message (no fabricated data).
    """
    q = str(query or "").strip()
    if not q:
        return {"found": False, "error": "No query provided"}
    # This build serves the reliable English endpoint only; refuse anything
    # else rather than silently returning en content for a different language.
    if lang not in (None, "en"):
        return {"found": False, "error": "Only lang=en is served by this build"}

    # Build a safe en.wikipedia /page/summary/<Title> URL. The REST endpoint
    # (verified to accept this exact shape) takes a single path segment with
    # spaces as underscores, and does NOT want the title percent-encoded
    # (encoding parentheses '()' yields HTTP 400). Neutralise only characters
    # that would break the URL path, then quote the result so the rest stays
    # safe but parens/hyphens survive unencoded.
    safe = q.translate(_SAFE_TITLE)
    url = f"{_WIKI}/{safe}"
    try:
        data = _get_json(url, timeout)
    except urllib.error.HTTPError as e:
        # 404 = the page does not exist; 301 variant = redirect resolved above.
        if e.code == 404:
            return {"found": False, "error": f"No article found for '{q}'"}
        return {"error": f"Upstream returned HTTP {e.code}"}
    except Exception as e:
        return {"error": f"Summary lookup failed: {str(e)[:200]}"}

    if not isinstance(data, dict) or data.get("type") == "disambiguation":
        return {"found": False, "error": f"No single article for '{q}' (disambiguation or non-page)"}

    # Normalise to a stable, bounded shape — never forward raw upstream noise.
    return {
        "found": True,
        "title": data.get("title"),
        "lang": lang,
        "wikidata_id": data.get("wikibase_item"),
        "description": _clean(data.get("description")),
        "extract": _clean(data.get("extract")),
        "extract_html": None,  # never forward HTML
        "thumbnail": (data.get("thumbnail") or {}).get("source"),
        "originalimage": (data.get("originalimage") or {}).get("source"),
        "content_urls": (data.get("content_urls") or {}).get("desktop", {}).get("page"),
        "url": data.get("content_urls", {}).get("desktop", {}).get("page")
        or data.get("canonicalurl"),
    }


def _clean(value):
    """Return None instead of an empty string, and strip whitespace."""
    if value is None:
        return None
    v = str(value).strip()
    return v or None
