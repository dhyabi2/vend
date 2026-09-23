"""Unit tests for the select module (CSS-selector structured extraction). No network hits."""
import select_endpoint as select


class _Resp:
    def __init__(self, status, text=""):
        self.status_code = status
        self.text = text


SAMPLE_HTML = """<html><head><title>Price Page</title></head><body>
<h1>Widget</h1>
<p class="price">12.99</p>
<p class="price">7.50</p>
<a href="/a">link one</a>
<a href="/b">link two</a>
<table><tr><td>r1c1</td></tr><tr><td>r2c1</td></tr></table>
</body></html>"""


def _fake_get(monkeypatch, resp):
    monkeypatch.setattr(select.httpx, "get", lambda *a, **k: resp)


def test_select_text_matches(monkeypatch):
    _fake_get(monkeypatch, _Resp(200, SAMPLE_HTML))
    out = select.select_from_url("https://shop.example/p", ".price")
    assert out["error"] is None
    assert out["title"] == "Price Page"
    assert out["count"] == 2
    assert [m["text"] for m in out["matches"]] == ["12.99", "7.50"]


def test_select_attribute_hrefs(monkeypatch):
    _fake_get(monkeypatch, _Resp(200, SAMPLE_HTML))
    out = select.select_from_url("https://shop.example/p", "a", attr="href")
    assert out["count"] == 2
    assert [m["value"] for m in out["matches"]] == ["/a", "/b"]


def test_select_limit_and_trimmed(monkeypatch):
    _fake_get(monkeypatch, _Resp(200, SAMPLE_HTML))
    out = select.select_from_url("https://shop.example/p", "a", limit=1)
    assert out["count"] == 1
    assert out["trimmed"] is True  # 2 matches, limit 1


def test_select_no_matches(monkeypatch):
    _fake_get(monkeypatch, _Resp(200, SAMPLE_HTML))
    out = select.select_from_url("https://shop.example/p", ".nope")
    assert out["error"] is None
    assert out["count"] == 0
    assert out["matches"] == []


def test_select_invalid_selector(monkeypatch):
    _fake_get(monkeypatch, _Resp(200, SAMPLE_HTML))
    out = select.select_from_url("https://shop.example/p", "[[[")
    assert out["error"] is not None and "selector" in out["error"]


def test_select_invalid_url():
    out = select.select_from_url("not-a-url", "h1")
    assert out["error"].startswith("invalid_url")


def test_select_missing_selector(monkeypatch):
    _fake_get(monkeypatch, _Resp(200, SAMPLE_HTML))
    out = select.select_from_url("https://shop.example/p", None)
    assert out["error"].startswith("missing_selector")


def test_select_http_error_no_charge(monkeypatch):
    _fake_get(monkeypatch, _Resp(404, "gone"))
    out = select.select_from_url("https://shop.example/p", "h1")
    assert out["error"].startswith("http_404")


def test_select_request_failure_no_charge(monkeypatch):
    def boom(*a, **k):
        raise select.httpx.ConnectError("no route")
    monkeypatch.setattr(select.httpx, "get", boom)
    out = select.select_from_url("https://shop.example/p", "h1")
    assert out["error"] is not None and out["error"].startswith("request_failed")
    assert not out["matches"]
