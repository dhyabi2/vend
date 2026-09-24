"""Unit tests for the batch_status module. No network is hit (injected fetch)."""
import batch_status


class _Resp:
    def __init__(self, status, url):
        self.status_code = status
        self._u = url

    @property
    def url(self):
        return self._u

    def __str__(self):
        return str(self._u)


def test_batch_status_happy_path(monkeypatch):
    calls = {}

    def fake_request(method, url, headers=None, timeout=None, follow_redirects=True):
        calls[url] = method
        return _Resp(200, url)

    monkeypatch.setattr(batch_status.httpx, "request", fake_request)
    out = batch_status.batch_status(
        ["https://a.example/1", "https://b.example/2"]
    )
    assert "error" not in out
    assert out["total"] == 2
    assert out["ok"] == 2
    assert out["failed"] == 0
    # results preserve input order
    assert [r["url"] for r in out["results"]] == [
        "https://a.example/1", "https://b.example/2"
    ]
    assert all(r["status_code"] == 200 for r in out["results"])
    # both URLs were requested with HEAD by default
    assert calls == {
        "https://a.example/1": "HEAD",
        "https://b.example/2": "HEAD",
    }


def test_batch_status_comma_string_input(monkeypatch):
    monkeypatch.setattr(
        batch_status.httpx, "request",
        lambda method, url, headers=None, timeout=None, follow_redirects=True:
            _Resp(200, url),
    )
    out = batch_status.batch_status(" https://a.example/1, ,https://b.example/2 ")
    assert out["total"] == 2
    assert out["ok"] == 2


def test_batch_status_failed_url_and_preserves_order(monkeypatch):
    def fake_request(method, url, headers=None, timeout=None, follow_redirects=True):
        if "good" in url:
            return _Resp(200, url)
        raise batch_status.httpx.ConnectError("no")
    monkeypatch.setattr(batch_status.httpx, "request", fake_request)
    out = batch_status.batch_status(["https://good.example", "https://bad.example"])
    assert out["ok"] == 1
    assert out["failed"] == 1
    first = out["results"][0]
    second = out["results"][1]
    assert first["url"] == "https://good.example" and first["status_code"] == 200
    assert second["url"] == "https://bad.example" and second["error"] == "connection_failed"


def test_batch_status_invalid_url():
    out = batch_status.batch_status(["not-a-url"])
    assert out["results"][0]["error"].startswith("invalid_url")


def test_batch_status_missing_and_empty():
    assert batch_status.batch_status(None)["error"].startswith("missing_urls")
    assert batch_status.batch_status([])["error"].startswith("no_urls")
    assert batch_status.batch_status("")["error"].startswith("no_urls")


def test_batch_status_default_method_fallback(monkeypatch):
    captured = {}

    def fake_request(method, url, headers=None, timeout=None, follow_redirects=True):
        captured["method"] = method
        return _Resp(200, url)

    monkeypatch.setattr(batch_status.httpx, "request", fake_request)
    batch_status.batch_status(["https://a.example"], method="PUT")
    assert captured["method"] == "HEAD"  # unknown method falls back to HEAD


def test_batch_status_cap_at_max_urls(monkeypatch):
    seen = []
    monkeypatch.setattr(
        batch_status.httpx, "request",
        lambda method, url, headers=None, timeout=None, follow_redirects=True:
            seen.append(url) or _Resp(200, url),
    )
    many = [f"https://x.example/{i}" for i in range(120)]
    out = batch_status.batch_status(many)
    assert out["total"] == batch_status.MAX_URLS  # capped at 50
    assert len(seen) == batch_status.MAX_URLS
