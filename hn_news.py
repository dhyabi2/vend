"""
Hacker News headline/story feed for Vend.

Wraps the free, keyless Hacker News Firebase API (the canonical Algolia-free
source; HN items carry title, url, score, author, time and comment counts) into
a clean, bounded JSON endpoint for agents doing tech-trend research, content
monitoring, competitive intelligence, or building news/curation agents. No
signup, no key, no per-call cost upstream — the paywall here is Vend's own.

Supported params (all optional):
  list   : which HN feed to read: top|new|best|ask|show|job (default "top")
  limit  : how many items to return (default 10, capped at 30)
  score  : minimum score filter for top/best (optional, e.g. 100)

Items are normalised to a clean union of fields (id, title, url, by, score,
time, comment_count, item_type) so the caller gets a stable shape regardless of
which fields the upstream item carries. Any single item fetch that fails is
honestly omitted — never replaced with fake data.

Uses only the Python standard library (urllib + json). Priced at 0.0001 XNO
per call.
"""

import json
import urllib.request
import urllib.parse

# The free keyless upstream feed: {list} returns an array of item ids; each
# id is fetched from /item/<id>.json.
HN_API = "https://hacker-news.firebaseio.com/v0"

# Cap on how many items we return per call to keep responses (and the number
# of upstream item fetches) bounded.
DEFAULT_LIMIT = 10
MAX_LIMIT = 30
# Guard against an absurdly large response from a hostile host.
MAX_BYTES = 2 * 1024 * 1024  # 2 MiB
# Per-item timeout is short: we fetch up to MAX_LIMIT items per call.
ITEM_TIMEOUT = 6
_UA = "Vend/0.1 (Nano pay-per-call API; paypercall.dev)"

# The HN feed lists we can read. Anything else is refused with a clean error
# (never forwarded silently, because the upstream only knows these).
SUPPORTED_LISTS = ("top", "new", "best", "ask", "show", "job")

# Fields every item is normalised to; the source may provide a subset.
ITEM_FIELDS = ("id", "title", "url", "by", "score", "time", "comment_count", "item_type")

# Map HN's internal "type" field to a stable caller-facing label.
_TYPE_LABEL = {
    "story": "story",
    "ask": "ask",
    "show": "show",
    "job": "job",
    "comment": "comment",
    "poll": "poll",
}


def _normalise_item(item):
    """Return a clean dict with only ITEM_FIELDS present (missing as None)."""
    t = _TYPE_LABEL.get(item.get("type"), str(item.get("type") or "unknown"))
    return {
        "id": item.get("id"),
        "title": item.get("title"),
        "url": item.get("url"),  # absent for ask/job items — keep None honestly
        "by": item.get("by"),
        "score": item.get("score"),
        "time": item.get("time"),
        # `descendants` is HN's comment count; label it clearly for the caller.
        "comment_count": item.get("descendants"),
        "item_type": t,
    }


def _fetch_json(url, timeout):
    """Fetch and parse a JSON URL, returning the parsed object or None on error."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": _UA, "Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = resp.read(MAX_BYTES + 1)
            if len(data) > MAX_BYTES:
                return None
            return json.loads(data.decode("utf-8", errors="replace"))
    except Exception:
        return None


def hn_news(list_name="top", limit=DEFAULT_LIMIT, score=None, timeout: int = ITEM_TIMEOUT) -> dict:
    """Read top/new/best/ask/show/job stories from Hacker News as clean JSON.

    Args:
        list_name: which HN feed (top|new|best|ask|show|job).
        limit: number of items to return (default 10, capped at 30).
        score: optional minimum score filter applied client-side to the fetched
            items (only meaningful for scored lists like top/best).
        timeout: per-item HTTP timeout in seconds.

    Returns:
        dict with keys: source, list, requested, returned, filtered, items
        (list of normalised item dicts), or error.
    """
    if list_name not in SUPPORTED_LISTS:
        return {"error": f"Unsupported list '{list_name}'. Choose one of: {', '.join(SUPPORTED_LISTS)}"}

    try:
        limit = max(1, min(int(limit), MAX_LIMIT))
    except (TypeError, ValueError):
        limit = DEFAULT_LIMIT

    ids = _fetch_json(f"{HN_API}/{list_name}stories.json", timeout=timeout)
    if not isinstance(ids, list) or not ids:
        return {"error": "Failed to fetch the item-id list from Hacker News"}

    items = []
    # Fetch and normalise up to `limit` headline-bearing items. We scan the id
    # list (bounded to MAX_LIMIT ids for safety) until we have `limit` items or
    # run out. Any single item that fails to fetch is honestly omitted.
    for iid in ids[:MAX_LIMIT]:
        if len(items) >= limit:
            break
        item = _fetch_json(f"{HN_API}/item/{iid}.json", timeout=timeout)
        if not isinstance(item, dict) or not item.get("title"):
            continue  # honestly omit items we could not fetch or that have no headline
        items.append(_normalise_item(item))

    # Optional minimum-score filter, applied after fetch.
    if score is not None:
        try:
            min_score = int(score)
        except (TypeError, ValueError):
            min_score = None
        if min_score is not None:
            filtered = [it for it in items if (it.get("score") or 0) >= min_score]
            items = filtered

    return {
        "source": "news.ycombinator.com",
        "list": list_name,
        "requested": limit,
        "returned": len(items),
        "items": items,
    }
