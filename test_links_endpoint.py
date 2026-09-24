"""
Tests for the /api/v1/links endpoint (Vend Link Extractor, 0.0001 XNO).

Covers law L68: a valid links call returns the page's links as structured JSON,
and malformed input or an unfetchable URL is refused politely with an error
rather than an exception (never a silent charge).
"""

import pytest

from links_endpoint import links_from_url


def test_valid_page_returns_links():
    res = links_from_url("https://nano.org")
    assert res.get("error") is None
    assert res.get("count") > 0
    assert res.get("title")
    first = res["links"][0]
    assert "href" in first
    assert "text" in first
    assert "absolute" in first
    assert "external" in first


def test_links_have_external_flag():
    res = links_from_url("https://nano.org")
    assert any(l["external"] in (True, False) for l in res["links"])


def test_invalid_url_refuses_politely():
    assert links_from_url("not-a-url")["error"]
    assert links_from_url("")["error"]
    assert links_from_url("ftp://example.com/x")["error"]
    assert links_from_url("file:///etc/passwd")["error"]


def test_unreachable_host_refuses_politely():
    res = links_from_url("https://nonexistent-host-xyz-12345.invalid/")
    assert res["error"]


def test_limit_caps_results_and_trims():
    res = links_from_url("https://nano.org", limit=5)
    assert res["count"] <= 5


def test_never_raises_on_any_input():
    # The law is: refuse with an error, never raise.
    for bad in [None, "", 123, "not-a-url", "https://nonexistent-host-xyz.invalid/"]:
        try:
            r = links_from_url(bad)
            assert r["error"], f"{bad!r} did not refuse"
        except Exception as e:  # noqa: BLE001
            pytest.fail(f"{bad!r} raised instead of refusing: {e!r}")
