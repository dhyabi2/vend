"""One-call status check for a URL — the highest-demand, cheapest-paid shape.

Measured on the discovery index: the most-called x402 category outside crypto is
the plain "is this endpoint/URL up?" check. ``check_link`` already answers most
of that, but a monitoring buyer also needs to know whether the **body content
changed** since the last call, which is the difference between paging someone at
3am and not.

This module is the single upstream for ``GET /api/v1/status``. It is deliberately
independent of ``check_link.py`` so the paid per-call price of the status
endpoint never drags the extraction/HTTP stack along, and so a change here can
never alter what ``/api/v1/check-link`` returns.

Response contract (all keys always present, so a caller never has to guess):

    url              str   the URL as requested
    final_url        str   where the request landed after redirects
    status_code      int   final HTTP status, or None when the request failed
    ok               bool  True only for 2xx/3xx (4xx and 5xx are "not ok")
    reachable        bool  True when an HTTP response came back at all
    response_time_ms int   wall time of the full (redirect-following) request
    redirect_chain   list  [{url, status_code}, ...] in order
    content_type     str   Content-Type of the final response
    content_length   int   body size in bytes (measured, not the header)
    tls              dict  {valid, days_to_expiry, issuer, subject, error}
    content_hash     str   sha256 of the body, or None when there is no body
    content         dict  {changed, previous_hash} vs the tracker's last hash
    checked_at       str   ISO-8601 UTC timestamp of this check
    error            str   human-readable failure, or None

The content-change check is deliberately *provided* by the caller's tracker
(``previous_hash``) rather than stored here: Vend holds no per-buyer state, so a
buyer that wants drift detection keeps the hash a metric system already holds.
"""

import datetime
import hashlib
import socket
import ssl
import time
import urllib.parse

import httpx

USER_AGENT = "Vend/0.1 (Nano pay-per-call API; paypercall.dev)/status"
MAX_BODY_BYTES = 2_000_000  # hash at most 2 MB — enough to detect drift, bounded cost


def _tls_info(url: str) -> dict:
    """Inspect the TLS certificate of an https URL.

    Returns valid=False with an error string for http:// URLs, so a caller that
    asked for a status check still gets a complete response shape.
    """
    info = {
        "valid": False,
        "days_to_expiry": None,
        "issuer": None,
        "subject": None,
        "error": None,
    }
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https":
        info["error"] = "not an https URL"
        return info
    host = parsed.hostname
    port = parsed.port or 443
    if not host:
        info["error"] = "no host in URL"
        return info

    ctx = ssl.create_default_context()
    try:
        with socket.create_connection((host, port), timeout=10) as sock:
            with ctx.wrap_socket(sock, server_hostname=host) as ssock:
                cert = ssock.getpeercert()
        if not cert:
            info["error"] = "no certificate returned"
            return info
        info["valid"] = True
        not_after = cert.get("notAfter")
        if not_after:
            expires = datetime.datetime.strptime(
                not_after, "%b %d %H:%M:%S %Y %Z"
            ).replace(tzinfo=datetime.timezone.utc)
            now = datetime.datetime.now(datetime.timezone.utc)
            info["days_to_expiry"] = (expires - now).days
        issuer = {k: v for pair in cert.get("issuer", ()) for k, v in pair}
        subject = {k: v for pair in cert.get("subject", ()) for k, v in pair}
        info["issuer"] = issuer.get("organizationName") or issuer.get("commonName")
        info["subject"] = subject.get("commonName")
    except ssl.SSLCertVerificationError as e:
        info["error"] = f"certificate verification failed: {str(e)[:120]}"
    except Exception as e:  # noqa: BLE001 — a status check must always answer
        info["error"] = f"tls check failed: {str(e)[:120]}"
    return info


def check_status(url: str, timeout: int = 15, previous_hash: str = None) -> dict:
    """One-call status check for *url*.

    Args:
        url: URL to check (must start with http:// or https://).
        timeout: HTTP timeout in seconds.
        previous_hash: sha256 of the body from an earlier call, if the buyer
            tracks it. When given, ``content.changed`` says whether the body
            moved.

    Returns:
        The response contract described in the module docstring.
    """
    checked_at = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    result = {
        "url": url,
        "final_url": None,
        "status_code": None,
        "ok": False,
        "reachable": False,
        "response_time_ms": None,
        "redirect_chain": [],
        "content_type": None,
        "content_length": None,
        "tls": {"valid": False, "days_to_expiry": None, "issuer": None, "subject": None, "error": None},
        "content_hash": None,
        "content": {"changed": None, "previous_hash": previous_hash or None},
        "checked_at": checked_at,
        "error": None,
    }

    if not url or not url.startswith(("http://", "https://")):
        result["error"] = "Invalid URL: must start with http:// or https://"
        return result

    # TLS first, and independently: a cert problem is a real status fact and must
    # not be hidden by an httpx exception message.
    result["tls"] = _tls_info(url)

    try:
        start = time.monotonic()
        with httpx.Client(
            timeout=timeout,
            follow_redirects=True,
            headers={"User-Agent": USER_AGENT, "Accept": "*/*"},
        ) as client:
            resp = client.get(url)
            body = resp.content[:MAX_BODY_BYTES]
        elapsed_ms = int((time.monotonic() - start) * 1000)

        result["status_code"] = resp.status_code
        result["reachable"] = True
        result["ok"] = 200 <= resp.status_code < 400
        result["response_time_ms"] = elapsed_ms
        result["final_url"] = str(resp.url)
        result["redirect_chain"] = [
            {"url": str(r.url), "status_code": r.status_code} for r in resp.history
        ]
        result["content_type"] = resp.headers.get("content-type")
        result["content_length"] = len(resp.content)
        result["content_hash"] = hashlib.sha256(body).hexdigest()
        if previous_hash:
            result["content"]["changed"] = result["content_hash"] != previous_hash
    except httpx.TimeoutException:
        result["error"] = f"Timeout checking {url} (limit: {timeout}s)"
    except httpx.ConnectError as e:
        result["error"] = f"Connection failed: {str(e)[:120]}"
    except Exception as e:  # noqa: BLE001 — never 500 a paid status call
        result["error"] = f"Check error: {str(e)[:120]}"

    return result
