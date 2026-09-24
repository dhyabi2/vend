"""
Web search — DuckDuckGo primary, Yahoo fallback, both free with no API key.

Returns structured search results (title, href, snippet) suitable
for agent consumption. No upstream API costs.

Priced at 0.0001 XNO per call (same as extract/check-link).
"""

import logging

from ddgs import DDGS

log = logging.getLogger("vend.web_search")

# ─── helpers ────────────────────────────────────────────────────────────────


def _extract_results(raw_results: list[dict]) -> list[dict]:
    """Normalise ddgs result dicts to {title, href, snippet}."""
    results = []
    seen = set()
    for r in raw_results:
        href = (r.get("href") or r.get("url") or "").strip()
        if not href or href in seen:
            continue
        seen.add(href)
        results.append(
            {
                "title": (r.get("title") or "").strip(),
                "href": href,
                "snippet": (r.get("body") or r.get("snippet") or "").strip(),
            }
        )
    return results


def _search_ddg(query: str, max_results: int) -> list[dict] | None:
    """Try DuckDuckGo.  Returns results or None on any failure."""
    try:
        with DDGS() as ddgs:
            return list(ddgs.text(query, max_results=max_results))
    except Exception as e:
        log.warning("DDG search for %r failed: %s", query, e)
        return None


def _search_yahoo(query: str, max_results: int) -> list[dict] | None:
    """Try Yahoo (via ddgs).  Returns results or None on any failure."""
    try:
        with DDGS() as ddgs:
            return list(ddgs.text(query, max_results=max_results, backend="yahoo"))
    except Exception as e:
        log.warning("Yahoo search for %r failed: %s", query, e)
        return None


# ─── backends, tried in order ───────────────────────────────────────────────

_BACKENDS = [
    ("DuckDuckGo", _search_ddg),
    ("Yahoo", _search_yahoo),
]


# ─── main entry ────────────────────────────────────────────────────────────


def web_search(query: str, max_results: int = 10) -> dict:
    """Search the web — tries DuckDuckGo first, falls back to Yahoo.

    Args:
        query: Search query string
        max_results: Max results to return (default 10, max 50)

    Returns:
        dict with keys: query, results (list of {title, href, snippet}),
        result_count, or error on failure.
    """
    if not query or not query.strip():
        return {"error": "query parameter is required"}

    query = query.strip()
    max_results = min(max(max_results, 1), 50)
    last_error = None

    for name, backend_fn in _BACKENDS:
        raw = backend_fn(query, max_results)
        if raw is not None and len(raw) > 0:
            results = _extract_results(raw)
            return {
                "query": query,
                "source": name,
                "results": results,
                "result_count": len(results),
            }
        last_error = raw  # None means exception logged by backend_fn

    msg = f"all search backends failed for query {query!r}"
    log.error(msg)
    return {"error": msg}