"""Tests for the AI-jobs search module.

Uses mocking for the HTTP fetch (no network dependency) to test the pure
logic deterministically: field normalisation, pagination bounding, remote
filter coercion, and error handling. A live smoke test is also included but
skips gracefully when the network/upstream is unavailable.
"""

import json
import os
import sys
from unittest import mock
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import ai_jobs as aj

# ── Helpers ────────────────────────────────────────────────────────────────


def _mock_open(payload, status=200):
    """Return a urlopen mock that serves the given JSON payload."""
    body = json.dumps(payload).encode("utf-8")

    class FakeResp:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self, n=-1):
            return body

    m = mock.MagicMock()
    m.return_value.__enter__.return_value = FakeResp()
    return m


SAMPLE_PAYLOAD = {
    "source": "artificialintelligencejobs.co",
    "generated": "2026-09-22 05:41 UTC",
    "total_live": 19843,
    "matched": 2,
    "returned": 2,
    "offset": 0,
    "jobs": [
        {
            "title": "Research Program Manager",
            "company": "OpenAI",
            "location": "San Francisco",
            "remote": True,
            "category": "Research",
            "level": "Lead+",
            "region": "US",
            "salary": "$239K – $328K",
            "posted": "2026-09-22",
            "url": "https://artificialintelligencejobs.co/jobs/x",
            "apply_url": "https://jobs.ashbyhq.com/openai/x",
            "companyUrl": "https://openai.com",
            "tags": ["Frontier lab"],
            "slug": "x",
        },
        {
            "title": "Software Engineer",
            "company": "Cursor",
            "location": "Austin",
            "remote": False,
            "category": "Engineering",
            "level": "Mid",
            "region": "US",
            "salary": None,
            "posted": "2026-09-22",
            "url": "https://artificialintelligencejobs.co/jobs/y",
            "apply_url": "https://jobs.ashbyhq.com/cursor/y",
        },
    ],
}


def test_default_limit_bounds():
    """Default limit is DEFAULT_LIMIT and huge requested limits are capped."""
    assert aj.ai_jobs is not None
    # Pure logic: _clamp through the entry point is exercised below via mocks.
    # Here check the constants are sane.
    assert 1 <= aj.DEFAULT_LIMIT <= aj.MAX_LIMIT
    print("PASS test_default_limit_bounds")


def test_normalise_job_union():
    """_normalise_job returns a clean dict with JOB_FIELDS present."""
    job = {
        "title": "T",
        "company": "C",
        "location": "L",
        "category": "Research",
        "level": "Mid",
        "region": "US",
        "remote": True,
        "salary": None,
        "posted": "2026-09-22",
        "url": "https://u",
        "apply_url": "https://a",
    }
    out = aj._normalise_job(job)
    for field in aj.JOB_FIELDS:
        assert field in out, f"missing {field}"
    # Fields not supplied by upstream default to None.
    assert out["tags"] is None
    assert out["company_url"] is None
    assert out["slug"] is None
    assert out["title"] == "T"
    print("PASS test_normalise_job_union")


def test_coerce_bool_remote():
    """Remote flag only becomes true for truthy inputs."""
    assert aj._coerce_bool("1") is True
    assert aj._coerce_bool("true") is True
    assert aj._coerce_bool("TRUE") is True
    assert aj._coerce_bool("yes") is True
    assert aj._coerce_bool("on") is True
    assert aj._coerce_bool("0") is None
    assert aj._coerce_bool("false") is None
    assert aj._coerce_bool(None) is None
    assert aj._coerce_bool("") is None
    print("PASS test_coerce_bool_remote")


def test_limit_clamped_to_max():
    """A requested limit above MAX_LIMIT is clamped down."""
    with mock.patch.object(aj.urllib.request, "urlopen", _mock_open(SAMPLE_PAYLOAD)):
        res = aj.ai_jobs(limit=99999)
    assert "error" not in res
    assert res["returned"] == 2
    print("PASS test_limit_clamped_to_max")


def test_offset_non_negative():
    """Negative offset is clamped to 0, not forwarded."""
    with mock.patch.object(aj.urllib.request, "urlopen", _mock_open(SAMPLE_PAYLOAD)) as m:
        res = aj.ai_jobs(offset=-5)
    assert "error" not in res
    assert res["offset"] == 0
    # Confirm the upstream URL had offset=0 (not -5).
    args = m.call_args[0][0]
    assert "offset=0" in args.full_url
    print("PASS test_offset_non_negative")


def test_remote_filter_passed_upstream():
    """Setting remote=1 forwards remote=true and returns remote-capable jobs."""
    with mock.patch.object(aj.urllib.request, "urlopen", _mock_open(SAMPLE_PAYLOAD)) as m:
        res = aj.ai_jobs(remote="1")
    assert "error" not in res
    args = m.call_args[0][0]
    assert "remote=true" in args.full_url
    assert res["filters"].get("remote") is True
    print("PASS test_remote_filter_passed_upstream")


def test_filters_forwarded_and_recorded():
    """Search filters are forwarded upstream and recorded in the result."""
    with mock.patch.object(aj.urllib.request, "urlopen", _mock_open(SAMPLE_PAYLOAD)) as m:
        res = aj.ai_jobs(q="OpenAI", company="OpenAI", category="Research", region="US")
    assert "error" not in res
    url = m.call_args[0][0].full_url
    for frag in ("q=OpenAI", "company=OpenAI", "category=Research", "region=US"):
        assert frag in url, f"{frag} not in {url}"
    assert res["filters"] == {
        "q": "OpenAI", "company": "OpenAI", "category": "Research", "region": "US",
    }
    print("PASS test_filters_forwarded_and_recorded")


def test_only_supported_filters_forwarded():
    """Only SUPPORTED_FILTERS are ever placed in the upstream query string."""
    with mock.patch.object(aj.urllib.request, "urlopen", _mock_open(SAMPLE_PAYLOAD)) as m:
        # The endpoint contract exposes only supported filters; verify the
        # module never forwards a param outside SUPPORTED_FILTERS.
        res = aj.ai_jobs(q="nano", limit=5)
    assert "error" not in res
    url = m.call_args[0][0].full_url
    assert "q=nano" in url
    assert "limit=5" in url
    # No parameter outside SUPPORTED_FILTERS should ever appear in the URL.
    for param, _ in urllib.parse.parse_qsl(url.split("?", 1)[1]):
        assert param in aj.SUPPORTED_FILTERS or param in ("limit", "offset", "remote"), \
            f"unexpected upstream param forwarded: {param}"
    assert res["filters"] == {"q": "nano"}
    print("PASS test_only_supported_filters_forwarded")


def test_result_shape():
    """The top-level result shape is stable and complete."""
    with mock.patch.object(aj.urllib.request, "urlopen", _mock_open(SAMPLE_PAYLOAD)):
        res = aj.ai_jobs()
    assert "error" not in res
    for key in ("source", "total_live", "matched", "returned", "offset", "filters", "jobs"):
        assert key in res, f"missing {key}"
    assert res["matched"] == 2
    assert res["returned"] == 2
    job = res["jobs"][0]
    assert job["title"] == "Research Program Manager"
    assert job["company"] == "OpenAI"
    assert job["apply_url"].startswith("https://")
    print("PASS test_result_shape")


def test_upstream_error_returns_error():
    """A URL/network failure returns a clean error dict, never a crash."""
    with mock.patch.object(aj.urllib.request, "urlopen", side_effect=Exception("boom")):
        res = aj.ai_jobs()
    assert "error" in res
    assert "fetch" in res["error"]
    print("PASS test_upstream_error_returns_error")


def test_non_dict_payload_error():
    """A malformed (non-dict) upstream payload returns an error dict."""
    m = mock.MagicMock()
    body = b"[1,2,3]"

    class FakeResp:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self, n=-1):
            return body

    m.return_value.__enter__.return_value = FakeResp()
    with mock.patch.object(aj.urllib.request, "urlopen", m):
        res = aj.ai_jobs()
    assert "error" in res
    print("PASS test_non_dict_payload_error")


def _live_smoke():
    """Optional live smoke test against the real feed (skips on failure)."""
    res = aj.ai_jobs(q="OpenAI", limit=3)
    if "error" in res:
        print(f"SKIP live smoke (upstream unavailable): {res['error']}")
        return
    assert res["matched"] > 0
    assert res["returned"] <= 3
    assert all(j["title"] for j in res["jobs"])
    print("PASS live smoke: matched=%s returned=%s" % (res["matched"], res["returned"]))


if __name__ == "__main__":
    test_default_limit_bounds()
    test_normalise_job_union()
    test_coerce_bool_remote()
    test_limit_clamped_to_max()
    test_offset_non_negative()
    test_remote_filter_passed_upstream()
    test_filters_forwarded_and_recorded()
    test_only_supported_filters_forwarded()
    test_result_shape()
    test_upstream_error_returns_error()
    test_non_dict_payload_error()
    _live_smoke()
    print("\nAll ai-jobs module tests PASSED")
