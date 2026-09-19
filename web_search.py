"""Web search using DuckDuckGo — free, no API key needed.

Returns structured search results (title, href, snippet) suitable
for agent consumption. No upstream API costs — DDG is free and
rate-limited generously.

Priced at 0.0001 XNO per call (same as extract/check-link).
"""

import logging
from typing import Optional

from ddgs import DDGS

log = logging.getLogger("vend.web_search")

# ─── main entry ────────────────────────────────────────────────────────────


def web_search(query: str, max_results: int = 10) -> dict:
    """Search the web using DuckDuckGo.

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

    try:
        with DDGS() as ddgs:
            raw_results = list(ddgs.text(query, max_results=max_results))
    except Exception as e:
        log.warning("DuckDuckGo search for %r failed: %s", query, e)
        return {"error": f"search backend error: {e}"}

    results = []
    seen = set()
    for r in raw_results:
        href = r.get("href", "") or ""
        title = r.get("title", "") or ""
        snippet = r.get("body", "") or ""

        # Deduplicate by href
        if href in seen:
            continue
        seen.add(href)

        results.append(
            {
                "title": title,
                "href": href,
                "snippet": snippet,
            }
        )

    return {
        "query": query,
        "results": results,
        "result_count": len(results),
    }