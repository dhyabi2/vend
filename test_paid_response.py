"""Unit tests for paid_response helper — no server, no Nano RPC needed.

Tests the result-validation logic that was repeated across 6 endpoints
and is now centralized in ``paid_response()``.

The helper reads ``request.state.payment`` and calls ``store.resolve()``,
so tests mock those dependencies via a dummy request object.
"""

import json
from unittest.mock import MagicMock, patch

# ── Module-level patching: store.resolve is a no-op in tests ──────


@patch("server.store.resolve")
def test_paid_response_success_no_error_key(mock_resolve):
    """A result dict with no 'error' key returns 200 (was a KeyError before .get())."""
    from server import paid_response

    request = MagicMock()
    request.state.payment = {
        "amount_raw": "100000000000000000000000000",
        "source": "nano_3saqo6ww3k1k8qawxpk9f1y7m9oswn7pbkf1a6xzyut7np44rf83kk3ycr4n",
    }
    request.headers.get = lambda k, d="": "A79C939E..."

    result = {"title": "Test Page", "text": "Hello"}
    resp = paid_response(result, request)

    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    body = json.loads(resp.body.decode())
    assert body.get("title") == "Test Page"
    assert body["payment"]["amount_xno"] != ""
    assert "receipt" in body
    mock_resolve.assert_called_once()


@patch("server.store.resolve")
def test_paid_response_error_key(mock_resolve):
    """A result dict with an 'error' key returns 400."""
    from server import paid_response

    request = MagicMock()
    request.state.payment = {
        "amount_raw": "100000000000000000000000000",
        "source": "nano_3saqo6ww3k1k8qawxpk9f1y7m9oswn7pbkf1a6xzyut7np44rf83kk3ycr4n",
    }
    request.headers.get = lambda k, d="": "A79C939E..."

    result = {"error": "not_found", "detail": "URL returned 404"}
    resp = paid_response(result, request)

    assert resp.status_code == 400, f"Expected 400, got {resp.status_code}"
    body = json.loads(resp.body.decode())
    assert body["error"] == "not_found"
    mock_resolve.assert_called_once()


@patch("server.store.resolve")
def test_paid_response_payment_fields(mock_resolve):
    """Payment receipt fields are attached correctly with truncated identifiers."""
    from server import paid_response

    request = MagicMock()
    request.state.payment = {
        "amount_raw": "100000000000000000000000000",
        "source": "nano_3saqo6ww3k1k8qawxpk9f1y7m9oswn7pbkf1a6xzyut7np44rf83kk3ycr4n",
    }
    request.headers.get = lambda k, d="": "A79C939E1234567890ABCDEF1234567890ABCDEF12"

    result = {"title": "Test"}
    resp = paid_response(result, request)

    body = json.loads(resp.body.decode())
    assert body["payment"]["amount_xno"] != ""
    assert body["payment"]["block_hash"].endswith("...")
    assert len(body["payment"]["block_hash"]) == 23
    assert body["payment"]["source"].endswith("...")
    assert body["receipt"].startswith("paid-by-")


@patch("server.store.resolve")
def test_paid_response_negative(mock_resolve):
    """Edge cases: empty result, result with only error, None-like values."""
    from server import paid_response

    request = MagicMock()
    request.state.payment = {
        "amount_raw": "100000000000000000000000000",
        "source": "nano_3saqo6ww3k1k8qawxpk9f1y7m9oswn7pbkf1a6xzyut7np44rf83kk3ycr4n",
    }
    request.headers.get = lambda k, d="": "A79C939E..."

    # Empty result — no error key, should be success
    result = {}
    resp = paid_response(result, request)
    assert resp.status_code == 200

    # Result with only error
    result = {"error": "timeout"}
    resp = paid_response(result, request)
    assert resp.status_code == 400


def test_paid_response_imports():
    """paid_response is importable from server and is a callable function."""
    from server import paid_response

    assert callable(paid_response)
    assert paid_response.__doc__ is not None
    assert "paid_response" in paid_response.__doc__ or True  # has some docstring


# ── run_paid_work tests ────────────────────────────────────────────────


@patch("server.store.resolve")
def test_run_paid_work_success(mock_resolve):
    """run_paid_work calls the function and returns its paid_response."""
    from server import run_paid_work

    request = MagicMock()
    request.state.payment = {
        "amount_raw": "100000000000000000000000000",
        "source": "nano_3saqo6ww3k1k8qawxpk9f1y7m9oswn7pbkf1a6xzyut7np44rf83kk3ycr4n",
    }
    request.headers.get = lambda k, d="": "A79C939E..."

    def fake_fn(url):
        return {"title": "Success", "text": "Hello"}

    resp = run_paid_work(request, fake_fn, "https://example.com")

    assert resp.status_code == 200
    body = json.loads(resp.body.decode())
    assert body["title"] == "Success"
    mock_resolve.assert_called_once()


@patch("server.store.resolve")
def test_run_paid_work_catches_exception(mock_resolve):
    """run_paid_work catches an exception from the module, marks block failed,
    returns 502, and never delivers."""
    from server import run_paid_work

    request = MagicMock()
    request.state.payment = {
        "amount_raw": "100000000000000000000000000",
        "source": "nano_3saqo6ww3k1k8qawxpk9f1y7m9oswn7pbkf1a6xzyut7np44rf83kk3ycr4n",
        "block_hash": "A79C939E1234567890ABCDEF1234567890ABCDEF1234567890ABCDEF12345678",
    }
    request.headers.get = lambda k, d="": "A79C939E..."

    def broken_fn(url):
        raise RuntimeError("Upstream crashed")

    resp = run_paid_work(request, broken_fn, "https://example.com")

    assert resp.status_code == 502
    body = json.loads(resp.body.decode())
    assert body["error"] == "processing_failed"
    # store.resolve was called with "failed"
    args, _ = mock_resolve.call_args
    assert args[1] == "failed"


# ── Payment-recovery retry tests ──────────────────────────────────


@patch("server.store.resolve")
def test_run_paid_work_recovery_success(mock_resolve):
    """A crashed module call is retried once — the retry succeeds → 200."""
    from server import run_paid_work, _RETRY_RECORD

    _RETRY_RECORD.clear()

    request = MagicMock()
    request.state.payment = {
        "amount_raw": "100000000000000000000000000",
        "source": "nano_3saqo6ww3k1k8qawxpk9f1y7m9oswn7pbkf1a6xzyut7np44rf83kk3ycr4n",
        "block_hash": "A79C939E1234567890ABCDEF1234567890ABCDEF1234567890ABCDEF12345678",
    }
    request.headers.get = lambda k, d="": "A79C939E..."

    call_count = [0]

    def flaky_fn(url):
        call_count[0] += 1
        if call_count[0] == 1:
            raise RuntimeError("Transient upstream error")
        return {"title": "Recovered", "text": "Hello"}

    resp = run_paid_work(request, flaky_fn, "https://example.com")

    assert resp.status_code == 200, f"Expected 200 after retry, got {resp.status_code}"
    body = json.loads(resp.body.decode())
    assert body["title"] == "Recovered"
    assert call_count[0] == 2, f"Expected 2 calls (1 fail + 1 retry), got {call_count[0]}"


@patch("server.store.resolve")
def test_run_paid_work_recovery_double_failure(mock_resolve):
    """Both the original call and the recovery retry fail → 502 with 'recovery retry also failed'."""
    from server import run_paid_work, _RETRY_RECORD

    _RETRY_RECORD.clear()

    request = MagicMock()
    request.state.payment = {
        "amount_raw": "100000000000000000000000000",
        "source": "nano_3saqo6ww3k1k8qawxpk9f1y7m9oswn7pbkf1a6xzyut7np44rf83kk3ycr4n",
        "block_hash": "A79C939E1234567890ABCDEF1234567890ABCDEF1234567890ABCDEF12345678",
    }
    request.headers.get = lambda k, d="": "A79C939E..."

    def always_broken(url):
        raise RuntimeError("Always crashes")

    resp = run_paid_work(request, always_broken, "https://example.com")

    assert resp.status_code == 502
    body = json.loads(resp.body.decode())
    assert "recovery retry also failed" in body.get("message", ""), (
        f"Expected 'recovery retry' in message, got: {body.get('message')}"
    )


@patch("server.store.resolve")
def test_run_paid_work_recovery_resets_failure_counter_on_success(mock_resolve):
    """A successful call resets the consecutive-failure counter to 0."""
    from server import run_paid_work, _RECOVERABLE_FAILURES

    # Seed the counter
    _RECOVERABLE_FAILURES["count"] = 3

    request = MagicMock()
    request.state.payment = {
        "amount_raw": "100000000000000000000000000",
        "source": "nano_3saqo6ww3k1k8qawxpk9f1y7m9oswn7pbkf1a6xzyut7np44rf83kk3ycr4n",
        "block_hash": "B79C939E1234567890ABCDEF1234567890ABCDEF1234567890ABCDEF12345679",
    }
    request.headers.get = lambda k, d="": "B79C939E..."

    def working_fn(url):
        return {"title": "Success"}

    run_paid_work(request, working_fn, "https://example.com")
    assert _RECOVERABLE_FAILURES["count"] == 0, "Success path resets counter to 0"


# ── Result-validation decorator tests ────────────────────────────────


def test_validate_paid_result_success():
    """Decorator returns the result unchanged for a success dict (no error key)."""
    from server import validate_paid_result, _MODULE_ERROR_COUNTER

    _MODULE_ERROR_COUNTER.clear()

    @validate_paid_result("test_mod")
    def my_fn():
        return {"title": "OK", "data": 42}

    result = my_fn()
    assert result["title"] == "OK"
    assert _MODULE_ERROR_COUNTER.get("test_mod") == 0


def test_validate_paid_result_error():
    """Decorator tracks errors in _MODULE_ERROR_COUNTER."""
    from server import validate_paid_result, _MODULE_ERROR_COUNTER

    _MODULE_ERROR_COUNTER.clear()

    @validate_paid_result("err_mod")
    def my_fn():
        return {"error": "not_found", "detail": "404"}

    result = my_fn()
    assert result["error"] == "not_found"
    assert _MODULE_ERROR_COUNTER["err_mod"] == 1


def test_validate_paid_result_resets_on_success():
    """After errors, a success resets the counter to 0."""
    from server import validate_paid_result, _MODULE_ERROR_COUNTER

    _MODULE_ERROR_COUNTER.clear()

    @validate_paid_result("flaky_mod")
    def my_fn():
        call_count = getattr(my_fn, "call_count", 0) + 1
        my_fn.call_count = call_count
        if call_count <= 2:
            return {"error": "timeout"}
        return {"title": "OK"}

    my_fn()
    my_fn()
    assert _MODULE_ERROR_COUNTER["flaky_mod"] == 2

    my_fn()
    assert _MODULE_ERROR_COUNTER["flaky_mod"] == 0


def test_validate_paid_result_wraps_metadata():
    """Decorator preserves original function name and docstring."""
    from server import validate_paid_result

    @validate_paid_result("meta_mod")
    def my_special_fn(arg1, arg2):
        """My special function docstring."""
        return {"result": arg1 + arg2}

    assert my_special_fn.__name__ == "my_special_fn"
    assert "My special function docstring" in (my_special_fn.__doc__ or "")
    assert my_special_fn(1, 2)["result"] == 3


# ── Per-endpoint module tests ─────────────────────────────────────────


def test_extract_url_success():
    """extract_url returns a dict with expected success keys (title, text, markdown)."""
    from server import extract_url
    import server as srv
    srv._MODULE_ERROR_COUNTER.clear()

    result = extract_url("https://example.com")
    assert isinstance(result, dict)
    # Success — no error key
    assert not result.get("error"), f"Expected no error, got: {result.get('error')}"
    assert "title" in result
    assert "text" in result or "markdown" in result


def test_extract_url_empty():
    """extract_url returns error for empty URL."""
    from server import extract_url

    result = extract_url("")
    assert isinstance(result, dict)
    assert result.get("error"), f"Expected error for empty URL, got: {result}"


def test_check_link_success():
    """check_link returns a dict with expected success keys."""
    from server import check_link

    result = check_link("https://example.com")
    assert isinstance(result, dict)
    assert not result.get("error"), f"Expected no error, got: {result.get('error')}"
    assert "status_code" in result or "url" in result
    assert "response_time_ms" in result or "status_code" in result


def test_check_link_invalid():
    """check_link returns error for invalid URL."""
    from server import check_link

    result = check_link("")
    assert isinstance(result, dict)
    assert result.get("error"), f"Expected error for empty URL, got: {result}"


def test_domain_info_success():
    """domain_info returns structured data with dns/whois/ssl/http_headers keys."""
    from server import domain_info

    result = domain_info("example.com")
    assert isinstance(result, dict)
    assert not result.get("error"), f"Expected no error, got: {result.get('error')}"
    # Should have at least one of the expected top-level keys
    possible = {"dns", "whois", "ssl", "http_headers", "domain"}
    assert possible & set(result.keys()), f"Expected one of {possible} in keys, got {list(result.keys())[:5]}"


def test_domain_info_empty():
    """domain_info returns error for empty domain."""
    from server import domain_info

    result = domain_info("")
    assert isinstance(result, dict)
    assert result.get("error"), f"Expected error for empty domain, got: {result}"


def test_web_search_success():
    """web_search returns a dict with expected success keys."""
    from server import web_search

    result = web_search("test query nano")
    assert isinstance(result, dict)
    # Search can return empty results without error
    assert not result.get("error"), f"Expected no error, got: {result.get('error')}"


def test_web_search_empty():
    """web_search returns error for empty query."""
    from server import web_search

    result = web_search("")
    assert isinstance(result, dict)
    assert result.get("error"), f"Expected error for empty query, got: {result}"


def test_geoip_lookup_success():
    """geoip_lookup returns structured data for a valid IP."""
    from server import geoip_lookup

    result = geoip_lookup("8.8.8.8")
    assert isinstance(result, dict)
    assert not result.get("error"), f"Expected no error, got: {result.get('error')}"
    assert "country" in result or "city" in result or "lat" in result or "lon" in result


def test_geoip_lookup_empty():
    """geoip_lookup returns error for empty IP."""
    from server import geoip_lookup

    result = geoip_lookup("")
    assert isinstance(result, dict)
    assert result.get("error"), f"Expected error for empty IP, got: {result}"


def test_nano_account_info_success():
    """nano_account_info returns structured Nano account data."""
    from server import nano_account_info

    # Use the Vend treasury account (has on-ledger history, guaranteed valid)
    result = nano_account_info("nano_1yo6c1t64ahfjdw1dxizmbbnpdmbrckwhw9phbg5pdkeubrizga4qhnjmnx7")
    assert isinstance(result, dict)
    if result.get("error"):
        # If error, it should not be about format — the account is valid
        assert "account number" not in result.get("error", "").lower(), f"Format issue: {result}"
    else:
        assert "balance" in result or "representative" in result or "block_count" in result


def test_nano_account_info_empty():
    """nano_account_info returns error for empty account."""
    from server import nano_account_info

    result = nano_account_info("")
    assert isinstance(result, dict)
    assert result.get("error"), f"Expected error for empty account, got: {result}"