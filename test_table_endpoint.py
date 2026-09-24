"""
Tests for /api/v1/table — HTML table extraction to structured JSON.

Mirrors test_meta_endpoint.py. Covers law L66: a valid call returns the page's
tables as structured rows; malformed input and unfetchable URLs are refused
with an error rather than an exception.
"""

import pytest

import table_endpoint

SAMPLE_HTML = """<!DOCTYPE html>
<html><head><title>Prices</title></head><body>
<table id="prices">
  <tr><th>Item</th><th>Price</th></tr>
  <tr><td>Apple</td><td>1.00</td></tr>
  <tr><td>Pear</td><td>2.00</td></tr>
</table>
</body></html>
"""


class _Fake:
    status_code = 200
    text = SAMPLE_HTML


def test_valid_table_returns_headers_and_rows(monkeypatch):
    def fake_get(url, headers=None, timeout=None, follow_redirects=None):
        return _Fake()

    monkeypatch.setattr(table_endpoint.httpx, "get", fake_get)
    res = table_endpoint.tables_for_url("https://example.com/prices")
    assert res["error"] is None
    assert res["count"] == 1
    t = res["tables"][0]
    assert t["headers"] == ["Item", "Price"]
    assert t["rows"][0] == {"Item": "Apple", "Price": "1.00"}
    assert t["rows"][1] == {"Item": "Pear", "Price": "2.00"}


def test_valid_table_headers_not_repeated_as_row(monkeypatch):
    """The <th> header row must not also appear as a data row."""
    def fake_get(url, headers=None, timeout=None, follow_redirects=None):
        return _Fake()

    monkeypatch.setattr(table_endpoint.httpx, "get", fake_get)
    res = table_endpoint.tables_for_url("https://example.com/prices")
    assert res["tables"][0]["rows"][0] != {"Item": "Item", "Price": "Price"}


def test_no_tables_returns_zero(monkeypatch):
    class NoTable:
        status_code = 200
        text = "<html><body><p>this page has no tables at all, it is just a paragraph of text for the test to confirm zero tables are returned</p></body></html>"

    def fake_get(url, headers=None, timeout=None, follow_redirects=None):
        return NoTable()

    monkeypatch.setattr(table_endpoint.httpx, "get", fake_get)
    res = table_endpoint.tables_for_url("https://example.com/")
    assert res["error"] is None
    assert res["count"] == 0
    assert res["tables"] == []


def test_bad_url_refuses_politely():
    res = table_endpoint.tables_for_url("not-a-url")
    assert res["error"].startswith("invalid_url")


def test_empty_url_refuses():
    res = table_endpoint.tables_for_url("")
    assert res["error"].startswith("invalid_url")


def test_non_http_refused():
    res = table_endpoint.tables_for_url("ftp://example.com/x")
    assert res["error"].startswith("invalid_url")


def test_non_200_refuses(monkeypatch):
    class Fake404:
        status_code = 404
        text = "<html>nf</html>"

    def fake_get(url, headers=None, timeout=None, follow_redirects=None):
        return Fake404()

    monkeypatch.setattr(table_endpoint.httpx, "get", fake_get)
    res = table_endpoint.tables_for_url("https://example.com/missing")
    assert res["error"] == "http_404 fetching https://example.com/missing"


def test_timeout_refuses(monkeypatch):
    class Boom(table_endpoint.httpx.TimeoutException):
        pass

    def fake_get(url, headers=None, timeout=None, follow_redirects=None):
        raise Boom("t")

    monkeypatch.setattr(table_endpoint.httpx, "get", fake_get)
    res = table_endpoint.tables_for_url("https://slow.example.com/")
    assert res["error"].startswith("timeout")


def test_request_error_refuses(monkeypatch):
    def fake_get(url, headers=None, timeout=None, follow_redirects=None):
        raise table_endpoint.httpx.RequestError("dns")

    monkeypatch.setattr(table_endpoint.httpx, "get", fake_get)
    res = table_endpoint.tables_for_url("https://nope.example.com/")
    assert res["error"].startswith("request_failed")
