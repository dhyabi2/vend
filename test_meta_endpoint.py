"""
Tests for /api/v1/meta — OpenGraph / Twitter / JSON-LD metadata extraction.

Mirrors the style of test_select_endpoint.py. Covers law L65: a valid call
returns the page's metadata; malformed input and unfetchable URLs are refused
with an error rather than an exception.
"""

import pytest

import meta_endpoint

# A tiny HTML page published as a fixture so the tests never depend on the
# live internet.
SAMPLE_HTML = """<!DOCTYPE html>
<html>
<head>
  <title>Example Product</title>
  <meta name="description" content="A demo product for tests.">
  <meta property="og:title" content="Example Product OG">
  <meta property="og:description" content="OG description here">
  <meta property="og:image" content="https://example.com/img.png">
  <meta property="og:type" content="product">
  <meta property="og:site_name" content="Example">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:image" content="https://example.com/tw.png">
  <link rel="canonical" href="https://example.com/products/1">
  <link rel="icon" href="/favicon.ico">
  <script type="application/ld+json">
  {"@context":"https://schema.org","@type":"Product","name":"Test Product"}
  </script>
</head>
<body><h1>Hello</h1></body>
</html>
"""


class _FakeResponse:
    status_code = 200
    text = SAMPLE_HTML


def test_valid_meta_returns_title_description_and_og(monkeypatch):
    class Fake:
        status_code = 200
        text = SAMPLE_HTML

    def fake_get(url, headers=None, timeout=None, follow_redirects=None):
        return Fake()

    monkeypatch.setattr(meta_endpoint.httpx, "get", fake_get)
    res = meta_endpoint.meta_for_url("https://example.com/products/1")
    assert res["error"] is None
    assert res["title"] == "Example Product"
    assert res["description"] == "A demo product for tests."
    assert res["og"]["title"] == "Example Product OG"
    assert res["og"]["image"] == "https://example.com/img.png"
    assert res["og"]["type"] == "product"
    assert res["twitter"]["card"] == "summary_large_image"
    assert res["canonical"] == "https://example.com/products/1"


def test_valid_meta_returns_favicon_and_jsonld(monkeypatch):
    def fake_get(url, headers=None, timeout=None, follow_redirects=None):
        return _FakeResponse()

    monkeypatch.setattr(meta_endpoint.httpx, "get", fake_get)
    res = meta_endpoint.meta_for_url("https://example.com/")
    assert res["favicon"] == "/favicon.ico"
    assert len(res["json_ld"]) == 1
    assert res["json_ld"][0]["@type"] == "Product"
    assert res["json_ld"][0]["name"] == "Test Product"


def test_bad_url_refuses_politely():
    res = meta_endpoint.meta_for_url("not-a-url")
    assert "error" in res
    assert res["error"].startswith("invalid_url")
    assert res["json_ld"] == []


def test_empty_url_refuses_politely():
    res = meta_endpoint.meta_for_url("")
    assert res["error"].startswith("invalid_url")


def test_non_http_scheme_refused():
    res = meta_endpoint.meta_for_url("ftp://example.com/x")
    assert res["error"].startswith("invalid_url")


def test_non_200_refuses_with_http_status(monkeypatch):
    class Fake404:
        status_code = 404
        text = "<html>not found</html>"

    def fake_get(url, headers=None, timeout=None, follow_redirects=None):
        return Fake404()

    monkeypatch.setattr(meta_endpoint.httpx, "get", fake_get)
    res = meta_endpoint.meta_for_url("https://example.com/missing")
    assert res["error"] == "http_404 fetching https://example.com/missing"


def test_timeout_refuses_with_error(monkeypatch):
    class Boom(meta_endpoint.httpx.TimeoutException):
        pass

    def fake_get(url, headers=None, timeout=None, follow_redirects=None):
        raise Boom("timed out")

    monkeypatch.setattr(meta_endpoint.httpx, "get", fake_get)
    res = meta_endpoint.meta_for_url("https://slow.example.com/")
    assert res["error"].startswith("timeout")


def test_request_error_refuses_with_error(monkeypatch):
    def fake_get(url, headers=None, timeout=None, follow_redirects=None):
        raise meta_endpoint.httpx.RequestError("dns failed")

    monkeypatch.setattr(meta_endpoint.httpx, "get", fake_get)
    res = meta_endpoint.meta_for_url("https://nope.example.com/")
    assert res["error"].startswith("request_failed")


def test_empty_body_refuses(monkeypatch):
    class Empty:
        status_code = 200
        text = "<html><head></head></html>"

    def fake_get(url, headers=None, timeout=None, follow_redirects=None):
        return Empty()

    monkeypatch.setattr(meta_endpoint.httpx, "get", fake_get)
    res = meta_endpoint.meta_for_url("https://example.com/")
    assert res["error"] == "empty_or_too_small_response"
