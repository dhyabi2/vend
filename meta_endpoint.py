"""
OpenGraph / Twitter Card / JSON-LD metadata extraction for Vend.

Fetches a public URL and returns the page's metadata in one paid call:
Open Graph tags, Twitter Card tags, the <title>, meta description,
canonical URL, favicon and any JSON-LD blocks. A data/scraping/research
agent uses it to unfurl a link into a preview card, enrich a record, or
read structured data (Article, Product, etc.) without scraping and
re-parsing the whole page.

Laws L64-L65 (minted in the ledger):
- L64: The /api/v1/meta endpoint is advertised on every surface a buyer
  reads at 0.0001 XNO on nano:mainnet with the single treasury account,
  and answers a bare probe with the 402 challenge.
- L65: A valid meta call returns the page's title/description/OpenGraph/
  Twitter/JSON-LD metadata, and malformed input or an unfetchable URL is
  refused with an error rather than an exception.
Only public content is returned; no login, no cookies, no buyer data.
"""

import json
import re
from typing import List, Optional

import httpx

DEFAULT_TIMEOUT = 15
MAX_JSONLD_CHARS = 20000
MAX_META_VALUE_CHARS = 2000


def _safe_jsonld(block: str) -> dict:
    """Return the JSON-LD block as a dict, or a compact string if it cannot
    be parsed cleanly. Never lets a bad upstream block raise."""
    try:
        parsed = json.loads(block)
        if isinstance(parsed, list):
            return {"@type": "array", "count": len(parsed), "items": parsed}
        if isinstance(parsed, dict):
            return parsed
        return {"value": str(parsed)[:MAX_JSONLD_CHARS]}
    except Exception:
        return {"raw": block[:MAX_JSONLD_CHARS]}


def _meta_value(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    value = " ".join(value.strip().split())
    return value[:MAX_META_VALUE_CHARS] or None


def meta_for_url(url: str, timeout: int = DEFAULT_TIMEOUT) -> dict:
    """Fetch `url`, parse its metadata, return a structured dict.

    Never raises. Returns keys: url, title, description, canonical, favicon,
    og (dict), twitter (dict), json_ld (list), error (on any failure).
    """
    result = {
        "url": url,
        "title": None,
        "description": None,
        "canonical": None,
        "favicon": None,
        "og": {},
        "twitter": {},
        "json_ld": [],
        "error": None,
    }

    # --- Validate input first: refuse politely, never charge on a bad call.
    if not url or not url.startswith(("http://", "https://")):
        result["error"] = "invalid_url: must start with http:// or https://"
        return result

    headers = {
        "User-Agent": "Vend/0.1 (Nano pay-per-call API; paypercall.dev)/meta",
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

    # --- Title
    m = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
    if m:
        result["title"] = _meta_value(m.group(1))

    # --- Meta tags: name/property -> content
    meta_re = re.compile(
        r"<meta[^>]+(?:name|property)=[\"']([^\"']+)[\"'][^>]*"
        r"(?:content|value)=[\"']([^\"']*)[\"']",
        re.IGNORECASE,
    )
    meta_re2 = re.compile(
        r"<meta[^>]+(?:content|value)=[\"']([^\"']*)[\"'][^>]*"
        r"(?:name|property)=[\"']([^\"']+)[\"']",
        re.IGNORECASE,
    )
    metas = {}
    for pat in (meta_re, meta_re2):
        for m in pat.finditer(html):
            if pat is meta_re:
                key, value = m.group(1).lower(), m.group(2)
            else:
                value, key = m.group(1), m.group(2).lower()
            metas.setdefault(key, _meta_value(value))

    result["description"] = metas.get("description")

    og = {}
    for k, v in metas.items():
        if k.startswith("og:"):
            og[k[3:]] = v
    result["og"] = {k: og[k] for k in
                    ["title", "description", "image", "url", "type", "site_name"]
                    if k in og}

    twitter = {}
    for k, v in metas.items():
        if k.startswith("twitter:"):
            twitter[k[8:]] = v
    result["twitter"] = twitter

    # --- Canonical link
    m = re.search(r'<link[^>]+rel=["\']canonical["\'][^>]*href=["\']([^"\']+)["\']',
                  html, re.IGNORECASE)
    if m:
        result["canonical"] = m.group(1)

    # --- Favicon
    m = re.search(r'<link[^>]+rel=["\'][^"\']*icon[^"\']*["\'][^>]*href=["\']([^"\']+)["\']',
                  html, re.IGNORECASE)
    if m:
        result["favicon"] = m.group(1)

    # --- JSON-LD blocks
    jsonld_blocks = re.findall(
        r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        html, re.IGNORECASE | re.DOTALL,
    )
    result["json_ld"] = [_safe_jsonld(block) for block in jsonld_blocks][:8]

    return result
