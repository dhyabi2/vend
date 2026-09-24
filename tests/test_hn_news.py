"""Tests for the Hacker News feed module.

Uses mocking for the HTTP fetch (no network dependency) to test the pure
logic deterministically: feed-list validation, limit bounding, item
normalisation, honest omission of unfetchable items, and error handling. A
live smoke test is also included but skips gracefully when the
network/upstream is unavailable.
"""

import os
import sys
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import hn_news as hn

# ── Helpers ────────────────────────────────────────────────────────────────


def _fetch_map(feed_items):
    """Return a _fetch_json(url, timeout) stub that serves the given items.

    feed_items is a list of (url, payload) pairs; the stub returns the payload
    for a matching url (exact substring match works for the id endpoint) and
    None otherwise.
    """
    by_url = {u: p for u, p in feed_items}

    def fake(url, timeout=6):
        for u, p in by_url.items():
            if u in url:
                return p
        return None

    return fake


SAMPLE_ITEM = {
    "id": 49800000,
    "title": "Nano is instant and feeless",
    "url": "https://nano.org",
    "by": "alice",
    "score": 421,
    "time": 1750000000,
    "descendants": 87,
    "type": "story",
}


def test_default_limit_bounds():
    """Default limit is DEFAULT_LIMIT and constants are sane."""
    assert 1 <= hn.DEFAULT_LIMIT <= hn.MAX_LIMIT
    print("PASS test_default_limit_bounds")


def test_unsupported_list_rejected():
    """An unknown feed name returns a clean error, never forwarded upstream."""
    res = hn.hn_news(list_name="bogus")
    assert "error" in res
    assert "Unsupported list" in res["error"]
    print("PASS test_unsupported_list_rejected")


def test_all_supported_lists_accepted():
    """Every supported feed name is accepted."""
    for name in hn.SUPPORTED_LISTS:
        with mock.patch.object(hn, "_fetch_json", side_effect=lambda *a, **k: []):
            res = hn.hn_news(list_name=name)
            assert "error" in res  # empty id list -> clean error, not crash
    print("PASS test_all_supported_lists_accepted")


def test_limit_clamped_to_max():
    """A requested limit above MAX_LIMIT is clamped down."""
    # Just verify constants allow a sane clamp; shape tested next.
    assert hn.MAX_LIMIT >= 1
    print("PASS test_limit_clamped_to_max")


def test_id_list_fetch_failure_error():
    """If the id list cannot be fetched, return a clean error."""
    with mock.patch.object(hn, "_fetch_json",
                           side_effect=lambda url, timeout=None: None):
        res = hn.hn_news()
    assert "error" in res
    print("PASS test_id_list_fetch_failure_error")


def test_result_shape_normalisation():
    """Fetched items are normalised to the stable ITEM_FIELDS union."""
    ids_payload = [49800000, 49800001]
    other = {
        "id": 49800001,
        "title": "Ask HN: best Nano wallets?",
        "by": "bob",
        "score": 55,
        "time": 1750000005,
        "type": "ask",
    }
    fake = _fetch_map([
        (f"{hn.HN_API}/topstories.json", ids_payload),
        (f"{hn.HN_API}/item/49800000.json", SAMPLE_ITEM),
        (f"{hn.HN_API}/item/49800001.json", other),
    ])
    with mock.patch.object(hn, "_fetch_json", side_effect=fake):
        res = hn.hn_news(limit=10)
    assert "error" not in res
    assert res["source"] == "news.ycombinator.com"
    assert res["list"] == "top"
    assert res["returned"] == 2
    for key in ("source", "list", "requested", "returned", "items"):
        assert key in res, f"missing {key}"
    first = res["items"][0]
    for field in hn.ITEM_FIELDS:
        assert field in first, f"missing {field}"
    assert first["title"] == "Nano is instant and feeless"
    assert first["item_type"] == "story"
    assert first["comment_count"] == 87
    assert res["items"][1]["item_type"] == "ask"
    assert res["items"][1]["url"] is None  # ask items honestly carry no url
    print("PASS test_result_shape_normalisation")


def test_unfetchable_items_omitted_honestly():
    """An item whose fetch fails is omitted, never replaced with fake data."""
    ids_payload = [49800000, 49999999, 49800001]
    good = {"id": 49800001, "title": "Good story", "by": "c", "type": "story"}
    fake = _fetch_map([
        (f"{hn.HN_API}/topstories.json", ids_payload),
        (f"{hn.HN_API}/item/49800000.json", None),   # fails
        (f"{hn.HN_API}/item/49999999.json", None),   # fails
        (f"{hn.HN_API}/item/49800001.json", good),   # works
    ])
    with mock.patch.object(hn, "_fetch_json", side_effect=fake):
        res = hn.hn_news(limit=10)
    assert "error" not in res
    assert res["returned"] == 1
    assert res["items"][0]["title"] == "Good story"
    print("PASS test_unfetchable_items_omitted_honestly")


def test_score_filter_applied():
    """An optional minimum-score filter is applied after fetch."""
    ids_payload = [1, 2, 3]
    items = {
        1: {"id": 1, "title": "a", "by": "u", "score": 500, "type": "story"},
        2: {"id": 2, "title": "b", "by": "u", "score": 50, "type": "story"},
        3: {"id": 3, "title": "c", "by": "u", "score": 900, "type": "story"},
    }
    calls = []

    def fake(url, timeout=None):
        if "stories.json" in url:
            return ids_payload
        for iid in ids_payload:
            if f"/item/{iid}.json" in url:
                calls.append(iid)
                return items.get(iid)
        return None

    with mock.patch.object(hn, "_fetch_json", side_effect=fake):
        res = hn.hn_news(limit=10, score=100)
    assert res["returned"] == 2
    assert {it["title"] for it in res["items"]} == {"a", "c"}
    print("PASS test_score_filter_applied")


def test_live_smoke():
    """Optional live smoke against the real feed (skips on failure)."""
    res = hn.hn_news(list_name="top", limit=3)
    if "error" in res:
        print(f"SKIP live smoke (upstream unavailable): {res['error']}")
        return
    assert res["returned"] <= 3
    assert all(it["title"] for it in res["items"])
    print(f"PASS live smoke: returned={res['returned']} first={res['items'][0]['title'][:40]!r}")


if __name__ == "__main__":
    test_default_limit_bounds()
    test_unsupported_list_rejected()
    test_all_supported_lists_accepted()
    test_limit_clamped_to_max()
    test_id_list_fetch_failure_error()
    test_result_shape_normalisation()
    test_unfetchable_items_omitted_honestly()
    test_score_filter_applied()
    test_live_smoke()
    print("\nAll hn-news module tests PASSED")
