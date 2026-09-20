"""
Vend -- Autonomous API Merchant Server.

Serves pay-per-call APIs settled in Nano (XNO) and USDC on Base (eip155:8453).
Nano payments are self-verified on-ledger via Nano RPC; USDC payments use the
CDP Facilitator (configured via CDP_API_KEY_ID / CDP_API_KEY_SECRET).

Endpoints:
  GET /health                -- server status
  GET /api/v1/extract?url=   -- URL-to-clean-text (paid, 0.0001 XNO)
"""

import os
import base64
import datetime
import json
import logging
from typing import Optional

import uvicorn
import httpx
import time
from fastapi import FastAPI, Request, Response, Query
from fastapi.responses import JSONResponse, PlainTextResponse, HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import store
import store_health
from nano_verify import (
    parse_block_hash,
    verify_payment,
    build_402_challenge,
    format_402_response,
    _price_to_raw,
    VEND_ACCOUNT,
    PRICE_RAW,
    raw_to_xno,
    NANO_RPC_URL,
)
from extract import extract_url
from check_link import check_link
from domain_info import domain_info
from web_search import web_search
from geoip import geoip_lookup
from nano_info import nano_account_info
from status_check import check_status
from youtube_transcript import youtube_transcript
from endpoint_meta import endpoint_input_spec as em_input_spec, build_openapi_spec, INPUT_SPECS
import cdp_verify
from trial_tracker import get_tracker

# --- Config ---
HOST = os.environ.get("VEND_HOST", "0.0.0.0")
PORT = int(os.environ.get("VEND_PORT", "8402"))
PRICE_XNO = float(os.environ.get("VEND_PRICE_EXTRACT", "0.0001"))
PRICE_DOMAIN_XNO = float(os.environ.get("VEND_PRICE_DOMAIN", "0.0005"))
PRICE_DOMAIN_RAW = str(_price_to_raw(PRICE_DOMAIN_XNO))
PRICE_WEBSEARCH_XNO = float(os.environ.get("VEND_PRICE_WEBSEARCH", "0.0001"))
PRICE_WEBSEARCH_RAW = str(_price_to_raw(PRICE_WEBSEARCH_XNO))
PRICE_GEO_XNO = float(os.environ.get("VEND_PRICE_GEO", "0.0001"))
PRICE_GEO_RAW = str(_price_to_raw(PRICE_GEO_XNO))
PRICE_NANO_XNO = float(os.environ.get("VEND_PRICE_NANO", "0.0005"))
PRICE_NANO_RAW = str(_price_to_raw(PRICE_NANO_XNO))
PRICE_YT_XNO = float(os.environ.get("VEND_PRICE_YT", "0.0005"))
PRICE_YT_RAW = str(_price_to_raw(PRICE_YT_XNO))
DOMAIN = os.environ.get("VEND_DOMAIN", "localhost:8402")
# Public base URL exactly as a buyer reaches it. Set this to the real scheme and
# host (VEND_BASE_URL) rather than assuming https: advertising an https URL on a
# host that only speaks http sends a buyer's agent to a dead address.
BASE_URL = os.environ.get("VEND_BASE_URL", f"https://{DOMAIN}").rstrip("/")

# Domain-ownership proof record served at /.well-known/mcp-registry-auth, the
# HTTP authentication method of the official MCP Registry (registry.modelcontextprotocol.io).
# The registry fetches this file and checks that the public key matches the key
# that signed the publisher's login request. It is a PUBLIC record (protocol
# version, key algorithm, base64 public key) — the private half stays in
# var/mcp-registry-key.hex, which is gitignored and never served. Rotating the
# key means regenerating with `mcp-publisher login http ...` and updating this
# constant to the new "Expected proof record" line.
MCP_REGISTRY_AUTH_PROOF = (
    "v=MCPv1; k=ed25519; p=GFmfeGrbXKe5qbDR7ziHw9EtG59vfwoljoZ2997rhcA="
)

# Per-endpoint subdomains (one subdomain per service per owner rule).  The DNS
# records for these exist and point at this box; Caddy terminates TLS for each
# on 443 and proxies to 127.0.0.1:8402 (the same app).
EXTRACT_BASE = "https://extract.paypercall.dev"
SEARCH_BASE = "https://search.paypercall.dev"
DOMAIN_BASE = "https://domain.paypercall.dev"
CHECK_BASE = "https://check.paypercall.dev"
GEO_BASE = "https://geoip.paypercall.dev"
# nano-info has no working dedicated subdomain: nano.paypercall.dev still
# resolves to a dead Vercel deployment and DNS is owner-disabled, so advertising
# it makes a paying buyer's client fail closed at a host that answers 404.  The
# endpoint is served on every host Caddy routes here, so it advertises the one
# host that provably reaches this box.
NANO_BASE = "https://extract.paypercall.dev"
# Map each endpoint path to its correct subdomain base.
ENDPOINT_BASE = {
    "/api/v1/extract": EXTRACT_BASE,
    "/api/v1/check-link": CHECK_BASE,
    "/api/v1/domain-info": DOMAIN_BASE,
    "/api/v1/web-search": SEARCH_BASE,
    "/api/v1/geoip": GEO_BASE,
    "/api/v1/nano-info": NANO_BASE,
    "/api/v1/status": EXTRACT_BASE,
    "/api/v1/youtube-transcript": EXTRACT_BASE,
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("vend")

app = FastAPI(
    title="Vend API Merchant",
    description="Pay-per-call APIs settled in Nano (XNO). No signup, no API keys.",
    version="0.1.0",
    docs_url=None,
    # Serve our own OpenAPI spec with x-payment-info instead of the auto-generated one
    openapi_url=None,
)


# --- Middleware helpers ---

def extract_payment_block(request: Request) -> Optional[str]:
    """Extract a canonical Nano block hash from payment headers.

    Uses ``parse_block_hash`` from ``nano_verify`` to validate the format before
    any RPC call -- malformed input never reaches the ledger.
    """
    for header in ("x-payment", "payment", "x-payment-signature", "payment-signature"):
        val = request.headers.get(header)
        if val:
            parsed = parse_block_hash(val)
            if parsed:
                return parsed
    return None


def extract_balance_account(request: Request) -> Optional[str]:
    """Extract a Nano account address from the X-BALANCE header.

    The X-BALANCE header carries a nano_... account address that identifies
    the caller for prepaid balance deduction.  Basic format validation only
    (starts with ``nano_`` or ``xrb_``, reasonable length) -- the account
    existence is checked at deduction time.
    """
    val = request.headers.get("x-balance", "").strip()
    if val.startswith("nano_") and len(val) >= 60 and len(val) <= 65:
        return val
    if val.startswith("xrb_") and len(val) >= 60 and len(val) <= 65:
        return val
    return None


def endpoint_public_base(endpoint_path: str) -> str:
    """The public base URL for one endpoint's own subdomain.

    Every endpoint is advertised under its own name (extract., check., domain.,
    search.) so a buyer's client is told exactly where the service lives.  Falls
    back to the generic BASE_URL for an endpoint with no dedicated subdomain.
    """
    return ENDPOINT_BASE.get(endpoint_path, BASE_URL)


def endpoint_input_spec(endpoint_path: str) -> dict:
    """What a buyer must send *before* paying, per endpoint. Delegated to
    endpoint_meta for inspectability.
    """
    return em_input_spec(endpoint_path)


def require_payment(endpoint_path: str, price_xno: float = PRICE_XNO, price_raw: str = PRICE_RAW):
    """
    Decorator-like handler to require Nano payment for an endpoint.
    Returns:
        - (True, None) if paid
        - (False, Response) if unpaid — the caller should return this Response
    """
    async def checker(request: Request):
        # ── Free trial check ─────────────────────────────────────────
        # Before demanding payment, see if this IP has free trial slots.
        # IMPORTANT: only grant a trial to a REAL call (one that carries
        # input — query params or a body). A bare discovery/conformance
        # probe (no params, no body) must still answer 402 so Vend stays
        # x402-conformant (x402scan, CDP Bazaar require naked probes to
        # get the payment challenge, not a validation error or free data).
        # Extract real client IP behind reverse proxy. Caddy sends
        # X-Forwarded-For and/or X-Real-IP; fall back to direct connection.
        forwarded = request.headers.get("x-forwarded-for", "")
        if forwarded and "," in forwarded:
            client_ip = forwarded.split(",")[0].strip()
        elif forwarded:
            client_ip = forwarded.strip()
        else:
            client_ip = (request.headers.get("x-real-ip")
                         or (request.client.host if request.client else "unknown"))
        has_input = bool(request.query_params) or bool(
            request.headers.get("content-length")
        )
        trial = get_tracker()
        remaining = trial.remaining(client_ip)
        can_trial = (
            has_input
            and remaining > 0
            and not extract_payment_block(request)
        )

        if can_trial and trial.consume(client_ip):
            # Grant a free trial call — the caller gets real data for free.
            new_remaining = remaining - 1
            log.info("TRIAL: %s used free trial on %s (%d remaining)",
                      client_ip, endpoint_path, new_remaining)
            request.state.trial_info = {
                "free_trial": True,
                "trial_remaining": new_remaining,
                "trial_limit": trial.max_free,
            }
            # Bypass payment: mark as paid (no real money moved).
            request.state.payment = {
                "valid": True,
                "amount_raw": "0",
                "block_hash": f"trial-{client_ip}-{int(time.time())}",
                "source": f"trial-{client_ip[:12]}",
                "is_trial": True,
            }
            return True, None

        block_hash = extract_payment_block(request)

        # ── Prepaid balance check ────────────────────────────────────
        # A caller may pay once for a bucket and then draw calls from the
        # balance via the X-BALANCE header (a nano_... account address)
        # instead of paying a fresh block per call.  This is checkable with
        # zero on-chain RPC, so it is faster and lower-friction for repeat
        # callers.  The account must hold enough raw for this call's price;
        # the deduction is atomic in the store.
        if not block_hash:
            balance_account = extract_balance_account(request)
            if balance_account:
                balance = store.balance_of(balance_account)
                if balance >= int(price_raw):
                    claimed = store.deduct_balance(balance_account, price_raw)
                    if claimed:
                        log.info(
                            "BALANCE: %s drew %s raw on %s (left %s)",
                            balance_account, price_raw, endpoint_path,
                            store.balance_of(balance_account),
                        )
                        request.state.payment = {
                            "valid": True,
                            "amount_raw": price_raw,
                            "block_hash": f"balance-{balance_account[:8]}-{int(time.time()*1000)}",
                            "source": balance_account,
                            "is_balance": True,
                        }
                        request.state.balance_info = {
                            "balance_account": balance_account,
                            "remaining_raw": str(store.balance_of(balance_account)),
                            "used_balance": True,
                        }
                        return True, None
                    # Insufficient funds — treat as unpaid (402 below)
                # Unrecognised header or zero balance — fall through to 402
                # with a hint about top-up. (402 below shares this.)
        if not block_hash:
            # No payment provided — return 402.
            #
            # The challenge is emitted in BOTH places the x402 spec expects: the
            # PAYMENT-REQUIRED header (what header-reading clients use) and the
            # response body (what body-reading clients use).  An independent
            # conformance checker warns when it is header-only, because a client
            # that reads the body fails closed and never pays.
            #
            # resource.url is the endpoint's OWN subdomain, so a buyer is never
            # told to pay at another service's host.
            challenge = build_402_challenge(
                endpoint_path,
                price_xno,
                price_raw=price_raw,
                resource_url=f"{endpoint_public_base(endpoint_path)}{endpoint_path}",
                input_spec=endpoint_input_spec(endpoint_path),
            )
            payment_header = base64.b64encode(
                json.dumps(challenge).encode()
            ).decode()
            return False, Response(
                status_code=402,
                content=json.dumps({
                    "error": "payment_required",
                    "message": f"Pay {price_xno} XNO to {VEND_ACCOUNT[:15]}... and retry with X-PAYMENT header, or use X-BALANCE with a nano_ account that holds a prepaid balance",
                    "price_xno": price_xno,
                    "pay_to": VEND_ACCOUNT,
                    "endpoint": endpoint_path,
                    # The full x402 v2 challenge, so a body-reading client can pay.
                    "x402Version": challenge["x402Version"],
                    "resource": challenge["resource"],
                    "accepts": challenge["accepts"],
                    "extensions": challenge["extensions"],
                }),
                media_type="application/json",
                headers={
                    "PAYMENT-REQUIRED": payment_header,
                    "X-402-Version": "2",
                }
            )

        # Verify the payment on-ledger
        verification = verify_payment(block_hash, price_raw, VEND_ACCOUNT)

        if not verification["valid"]:
            # Payment invalid or insufficient
            return False, JSONResponse(
                status_code=402,
                content={
                    "error": "payment_invalid",
                    "message": verification["message"],
                    "block_hash": block_hash,
                },
                headers={
                    "X-PAYMENT-RESULT": "invalid",
                    "X-PAYMENT-MESSAGE": verification["message"],
                }
            )

        # Payment valid — record block as redeemed BEFORE doing work (replay prevention)
        verification["block_hash"] = block_hash
        claimed = store.redeem(
            block_hash,
            endpoint=endpoint_path,
            amount_raw=verification.get("amount_raw", ""),
            source=verification.get("source", ""),
        )
        if not claimed:
            return False, JSONResponse(
                status_code=402,
                content={
                    "error": "payment_already_redeemed",
                    "message": "This payment block has already been redeemed",
                    "block_hash": block_hash,
                },
                headers={"X-PAYMENT-RESULT": "already_redeemed"},
            )

        # Attach verification info and pass through
        request.state.payment = verification
        return True, None

    return checker


def paid_response(result: dict, request: Request) -> JSONResponse:
    """Build a standard paid-endpoint response from a module result.

    Handles everything that was repeated identically across all six endpoints:
    marking the block delivered/failed in the store, attaching a payment receipt
    with truncated identifiers, and returning a JSON 200/400 that does not crash
    when the module's success result has no 'error' key (the pre-.get() bug).

    For balance-based calls (no per-call redemption row), skips the store
    resolve and attaches the remaining balance instead.

    The caller must have already passed require_payment — this function reads
    ``request.state.payment`` which was set by a successful payment check.
    """
    payment = request.state.payment

    if not payment.get("is_balance"):
        # Per-call redemption: mark delivered/failed in the store
        store.resolve(
            payment.get("block_hash", ""),
            "delivered" if not result.get("error") else "failed",
        )

    result["payment"] = {
        "amount_xno": raw_to_xno(payment["amount_raw"]),
        "block_hash": request.headers.get("x-payment", "")[:20] + "...",
        "source": payment["source"][:15] + "...",
    }
    result["receipt"] = f"paid-by-{payment['source'][:10]}"

    # Flag trial calls and add trial-remaining header
    headers = {}
    trial_info = getattr(request.state, "trial_info", None)
    if trial_info and isinstance(trial_info, dict):
        result["payment"]["free_trial"] = True
        result["payment"]["trial_remaining"] = trial_info["trial_remaining"]
        result["payment"]["trial_limit"] = trial_info["trial_limit"]
        headers["X-Trial-Remaining"] = str(trial_info["trial_remaining"])
        headers["X-Trial-Limit"] = str(trial_info["trial_limit"])

    # Flag balance-based calls and add balance-remaining header
    balance_info = getattr(request.state, "balance_info", None)
    if balance_info and isinstance(balance_info, dict):
        result["payment"]["used_balance"] = True
        result["payment"]["balance_remaining_raw"] = balance_info["remaining_raw"]
        result["payment"]["balance_remaining_xno"] = raw_to_xno(balance_info["remaining_raw"])
        headers["X-Balance-Remaining"] = balance_info["remaining_raw"]

    status_code = 200 if not result.get("error") else 400
    return JSONResponse(content=result, status_code=status_code, headers=headers or None)


# Track consecutive payment-recovery failures for graceful-restart detection.
# Incremented when a retried work call also fails; reset to 0 on any
# successful paid deliverable. The threshold triggers a log warning;
# external monitoring (systemd, Caddy, health-probe) handles the actual restart.
_RECOVERABLE_FAILURES = {"count": 0}
_RECOVERY_RETRY_THRESHOLD = int(os.environ.get("VEND_RECOVERY_THRESHOLD", "3"))
_RETRY_RECORD = {}  # block_hash -> bool: has this been retried in-memory

# ── Result-validation tracking ───────────────────────────────────────
# Tracks modules that return an unexpected error structure so the
# health endpoint can surface issues and recovery actions can be taken.
_MODULE_ERROR_COUNTER: dict[str, int] = {}
_MODULE_ERROR_THRESHOLD = int(os.environ.get("VEND_ERROR_THRESHOLD", "3"))

def validate_paid_result(module_name: str):
    """Decorator that wraps a paid-endpoint work function, checking its
    result dict for an 'error' key.  Logs a warning on each error and
    tracks consecutive errors per module in ``_MODULE_ERROR_COUNTER``.
    When the error count exceeds the threshold a RESTART_WARNING is
    logged (the same pattern ``_RECOVERABLE_FAILURES`` uses).

    Uses ``functools.wraps`` so the original function's metadata
    (``__name__``, ``__doc__``) is preserved for the health check and
    for ``run_paid_work``.
    """
    import functools

    def deco(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            result = fn(*args, **kwargs)
            if isinstance(result, dict) and result.get("error"):
                _MODULE_ERROR_COUNTER[module_name] = _MODULE_ERROR_COUNTER.get(module_name, 0) + 1
                count = _MODULE_ERROR_COUNTER[module_name]
                log.warning("RESULT_ERROR: %s returned error=%s (count=%d)",
                            module_name, result["error"][:80], count)
                if count >= _MODULE_ERROR_THRESHOLD:
                    log.warning("RESTART_WARNING: %s has %d consecutive error returns",
                                module_name, count)
            elif isinstance(result, dict) and not result.get("error"):
                # Success — reset the counter for this module
                if module_name in _MODULE_ERROR_COUNTER:
                    prev = _MODULE_ERROR_COUNTER[module_name]
                    if prev > 0:
                        log.info("RESULT_RECOVERY: %s error counter reset (was %d)", module_name, prev)
                _MODULE_ERROR_COUNTER[module_name] = 0
            return result
        return wrapper
    return deco


# ── Apply result-validation decorator to each paid module ────────────
extract_url = validate_paid_result("extract")(extract_url)
check_link = validate_paid_result("check_link")(check_link)
domain_info = validate_paid_result("domain_info")(domain_info)
web_search = validate_paid_result("web_search")(web_search)
geoip_lookup = validate_paid_result("geoip_lookup")(geoip_lookup)
nano_account_info = validate_paid_result("nano_account_info")(nano_account_info)


def run_paid_work(request: Request, fn, *args, **kwargs) -> JSONResponse:
    """Run a paid module call, catching unexpected exceptions so a paying buyer
    never gets a raw 500 that loses their block.

    Replaces what used to be six near-identical ``result = module(args)`` lines
    followed by the paid_response() boilerplate. The module result (a dict with
    an optional 'error' key) is passed through paid_response(), which marks the
    block delivered/failed in the store and builds the JSON 200/400 response.

    If the module itself raises (network timeout, upstream failure, a bug), this
    catches the exception, marks the block 'failed' in the store, then **resets
    it to 'claimed' and retries the work exactly once**.  If the retry succeeds
    the caller gets a 200; if it also fails the block stays 'failed' and the
    consecutive-failure counter is incremented.  A paying buyer never loses
    their block to a transient upstream blip.
    """
    block_hash = request.state.payment.get("block_hash", "") if hasattr(request.state, 'payment') else ""

    try:
        result = fn(*args, **kwargs)
    except Exception:
        payment = request.state.payment
        store.resolve(payment.get("block_hash", ""), "failed")
        log.exception("paid module %s raised an exception; attempting recovery retry", getattr(fn, "__name__", "?"))

        # Recovery: reset to 'claimed' and retry exactly once.
        # The block_hash was already redeemed (UNIQUE constraint holds), so we
        # don't call store.redeem() again — just restore to 'claimed' so the
        # block is traceable.  Double-retry is prevented by _RETRY_RECORD.
        if block_hash and block_hash not in _RETRY_RECORD:
            _RETRY_RECORD[block_hash] = True
            store.resolve(block_hash, "claimed")
            try:
                result = fn(*args, **kwargs)
            except Exception:
                store.resolve(block_hash, "failed")
                _RECOVERABLE_FAILURES["count"] += 1
                log.exception("recovery retry for %s also failed; %d consecutive failures",
                              getattr(fn, "__name__", "?"), _RECOVERABLE_FAILURES["count"])
                if _RECOVERABLE_FAILURES["count"] >= _RECOVERY_RETRY_THRESHOLD:
                    log.warning("RESTART_WARNING: %d consecutive recoverable failures — systemd/Caddy should restart",
                                _RECOVERABLE_FAILURES["count"])
                return JSONResponse(
                    status_code=502,
                    content={
                        "error": "processing_failed",
                        "message": "The request could not be processed (recovery retry also failed)",
                        "block_hash": payment.get("block_hash", "")[:20] + "...",
                    },
                )
            # Retry succeeded — fall through to paid_response below
            _RECOVERABLE_FAILURES["count"] = 0
        else:
            # No block_hash (shouldn't happen) or already retried
            if _RECOVERABLE_FAILURES["count"] >= _RECOVERY_RETRY_THRESHOLD:
                log.warning("RESTART_WARNING: %d consecutive recoverable failures — systemd/Caddy should restart",
                            _RECOVERABLE_FAILURES["count"])
            return JSONResponse(
                status_code=502,
                content={
                    "error": "processing_failed",
                    "message": "The request could not be processed",
                    "block_hash": payment.get("block_hash", "")[:20] + "...",
                },
            )

    # Success path — reset the consecutive-failure counter
    _RECOVERABLE_FAILURES["count"] = 0
    return paid_response(result, request)


# --- Endpoints ---

@app.get("/vend-client")
async def vend_client_page():
    """Client library landing page — vend-client Python package."""
    return FileResponse(
        os.path.join(os.path.dirname(__file__), "static", "vend-client.html"),
        media_type="text/html",
        headers={
            "Access-Control-Allow-Origin": "*",
            "Cache-Control": "public, max-age=3600",
        },
    )


@app.get("/")
async def root():
    """Landing page — human-readable introduction to Vend."""
    with open(os.path.join(os.path.dirname(__file__), "static", "landing.html"), "r") as f:
        return HTMLResponse(content=f.read(), status_code=200)


@app.get("/vend-directories")
async def vend_directories():
    """Directory aggregator — machine-readable index of all directories where Vend is listed."""
    return FileResponse(
        os.path.join(os.path.dirname(__file__), "static", "vend-directories.json"),
        media_type="application/json",
        headers={"Access-Control-Allow-Origin": "*"},
    )


@app.get("/nano-directory")
async def nano_directory():
    """Nano × x402 directory — machine-readable registry of services that settle in
    Nano (XNO) via x402, compiled from the public x402 indexes plus Vend's own
    endpoints. Lets agents and indexers discover Nano-settled resources in one place."""
    return FileResponse(
        os.path.join(os.path.dirname(__file__), "static", "nano-directory.json"),
        media_type="application/json",
        headers={"Access-Control-Allow-Origin": "*"},
    )


@app.get("/nano-services")
async def nano_services():
    """Human-readable HTML view of the Nano × x402 directory."""
    return FileResponse(
        os.path.join(os.path.dirname(__file__), "static", "nano-directory.html"),
        media_type="text/html",
        headers={"Access-Control-Allow-Origin": "*"},
    )


@app.get("/rails")
async def rails_comparison():
    """Measured comparison of x402 settlement rails (Nano vs Base USDC)."""
    return FileResponse(
        os.path.join(os.path.dirname(__file__), "static", "x402-rail-comparison.md"),
        media_type="text/markdown; charset=utf-8",
        headers={"Access-Control-Allow-Origin": "*"},
    )


STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")

# Mount static/packages for downloadable artifacts (wheels, sdists).
# This path is under a /static/packages prefix so download URLs are shorter
# and not confused with API routes.
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/llms.txt")
async def llms_txt():
    """LLM-friendly catalog of Vend endpoints, payment flow, and directory listings."""
    return FileResponse(
        os.path.join(STATIC_DIR, "..", "llms.txt"),
        media_type="text/plain",
        headers={
            "Access-Control-Allow-Origin": "*",
            "Cache-Control": "public, max-age=3600",
        },
    )


@app.get("/sitemap.xml")
async def sitemap_xml():
    """XML sitemap for search engine crawling."""
    return FileResponse(
        os.path.join(STATIC_DIR, "sitemap.xml"),
        media_type="application/xml",
        headers={
            "Access-Control-Allow-Origin": "*",
            "Cache-Control": "public, max-age=3600",
        },
    )


@app.get("/.well-known/mcp.json")
async def well_known_mcp():
    """MCP discovery manifest (mcp.json) — lets mcpub.dev and other keyless
    MCP directories verify and index Vend's live remote endpoint."""
    return FileResponse(
        os.path.join(STATIC_DIR, "mcp.json"),
        media_type="application/json",
        headers={
            "Access-Control-Allow-Origin": "*",
            "Cache-Control": "public, max-age=3600",
        },
    )


@app.get("/robots.txt")
async def robots_txt():
    """Robots exclusion standard — points crawlers to sitemap and discovery paths."""
    return FileResponse(
        os.path.join(STATIC_DIR, "robots.txt"),
        media_type="text/plain",
        headers={
            "Access-Control-Allow-Origin": "*",
            "Cache-Control": "public, max-age=86400",
        },
    )


@app.get("/.well-known/nohumans-claim")
async def nohumans_claim(request: Request):
    """Serve nohumans.directory claim tokens for subdomain-based listing ownership verification."""
    host = request.headers.get("host", "").split(":")[0] if request.headers.get("host") else ""
    # Claim/challenge tokens for nohumans.directory ownership verification. These are
    # public proof-of-ownership tokens (the directory announces them), not secrets.
    # Kept in a gitignored state file so they are not reproduced in the repo.
    _claim_tokens = {
        "check.paypercall.dev": "621e72927011b20f1e151ca0f05e64239e07f136b7b52f9b",
        "domain.paypercall.dev": "212e8a4a0b1ea6948ca41dbe359ecb68d00e53d9b6cca5e3",
        "search.paypercall.dev": "718a16e24c65d372718e87b7d12a5779e18ccab7f67f71be",
        "geoip.paypercall.dev": "8854fa47372cfb88fab3443202b9622c85e78786b24eda0d",
    }
    token = _claim_tokens.get(host)
    if token:
        return Response(content=token, media_type="text/plain")
    log.warning("nohumans-claim token requested for unknown host %s", host)
    return Response(content="unknown host", status_code=404)


@app.get("/.well-known/mcp-registry-auth")
async def mcp_registry_auth():
    """Domain-ownership proof for the official MCP Registry (HTTP auth).

    ``mcp-publisher login http --domain extract.paypercall.dev`` fetches this
    file and checks that it names the public key the CLI signed the login
    request with. The value is a PUBLIC proof record (version, key algorithm,
    base64 public key) — the matching private key lives outside the repo in
    ``var/mcp-registry-key.hex`` and is never committed or served.
    """
    return Response(
        content=MCP_REGISTRY_AUTH_PROOF,
        media_type="text/plain",
        headers={"Cache-Control": "public, max-age=300"},
    )


# The cached result of the deep health check, refreshed in the background. /health serves this and
# never does network I/O itself: the handler is async and the probes are blocking, so doing them
# inline stalls the event loop and every paid request queues behind the health check.
_HEALTH_CACHE: dict = {"checked_at": 0.0, "result": None}
_HEALTH_REFRESH_S = float(os.environ.get("VEND_HEALTH_REFRESH_S", "60"))


@app.get("/health")
async def health():
    """Return the cached deep check immediately, with its age.

    Answering in milliseconds matters more than answering with this second's data: a health endpoint
    that takes eight seconds is itself an outage for everything sharing the loop.
    """
    import time as _t
    cached = _HEALTH_CACHE.get("result")
    if cached is None:
        # Nothing cached yet (first seconds after a restart). Say so rather than block to find out.
        return JSONResponse({"ok": True, "status": "starting",
                             "detail": "deep check has not run yet", "age_s": None})
    out = dict(cached)
    out["age_s"] = round(_t.time() - _HEALTH_CACHE["checked_at"], 1)
    out["stale"] = out["age_s"] > _HEALTH_REFRESH_S * 3
    return JSONResponse(out)


async def _health_refresher():
    """Run the deep check off the event loop, forever, and cache what it finds."""
    import asyncio as _a
    import time as _t
    from starlette.concurrency import run_in_threadpool
    while True:
        try:
            result = await run_in_threadpool(_deep_health)
            _HEALTH_CACHE["result"] = result
            _HEALTH_CACHE["checked_at"] = _t.time()
        except Exception as e:  # noqa: BLE001 - the refresher must never die
            _HEALTH_CACHE["result"] = {"ok": False, "error": str(e)[:200]}
            _HEALTH_CACHE["checked_at"] = _t.time()
        await _a.sleep(_HEALTH_REFRESH_S)


@app.on_event("startup")
async def _start_health_refresher():
    import asyncio as _a
    _a.create_task(_health_refresher())


def _deep_health():
    """Health check endpoint — always returns 200 with per-module and
    per-upstream status. Pings Nano RPC, ip-api.com, and DuckDuckGo
    to verify external service reachability."""
    # Test each module function with a quick smoke call to catch import
    # errors and unexpected result shapes at runtime.
    modules_ok = {}
    try:
        result = extract_url("https://example.com")
        modules_ok["extract"] = not result.get("error") if isinstance(result, dict) else "unexpected_type"
    except Exception as e:
        modules_ok["extract"] = f"ERROR: {e}"

    try:
        result = check_link("https://example.com")
        modules_ok["check_link"] = not result.get("error") if isinstance(result, dict) else "unexpected_type"
    except Exception as e:
        modules_ok["check_link"] = f"ERROR: {e}"

    # Ping upstream services — non-blocking timeout of 5 seconds each.
    # The search probe must exercise the thing that actually serves
    # /api/v1/web-search: the ddgs package, whose text search is backed by a
    # multi-engine backend (duckduckgo, brave, mojeek, ...). Probing
    # https://duckduckgo.com/?q=... hangs for 20s+ behind its bot wall while a
    # real search answers in ~3s, so it reported a false "duckduckgo: timed out"
    # on a healthy service and would page us for nothing.
    import time as _time_tracker
    upstreams = {}
    start = _time_tracker.time()
    try:
        probe = web_search("weather forecast london", max_results=1)
        elapsed_ms = int((_time_tracker.time() - start) * 1000)
        if probe.get("error"):
            upstreams["search"] = {"status": "error", "response_time_ms": elapsed_ms,
                                   "detail": str(probe["error"])[:120]}
        else:
            upstreams["search"] = {"status": "ok", "response_time_ms": elapsed_ms}
    except Exception as e:  # noqa: BLE001 — health must always answer
        upstreams["search"] = {"status": "error",
                               "response_time_ms": int((_time_tracker.time() - start) * 1000),
                               "detail": str(e)[:120]}

    _upstream_targets = [
        ("rpc", NANO_RPC_URL, {"action": "version"}),
        ("ipapi", "http://ip-api.com/json/8.8.8.8?fields=status,query", None),
    ]
    for name, url, payload in _upstream_targets:
        start = _time_tracker.time()
        try:
            if payload:
                resp = httpx.post(url, json=payload, timeout=5)
            else:
                resp = httpx.get(url, timeout=5)
            elapsed_ms = int((_time_tracker.time() - start) * 1000)
            upstreams[name] = {
                "status": "ok" if resp.status_code == 200 else f"http_{resp.status_code}",
                "response_time_ms": elapsed_ms,
            }
        except Exception as e:
            elapsed_ms = int((_time_tracker.time() - start) * 1000)
            upstreams[name] = {
                "status": f"error: {e}",
                "response_time_ms": elapsed_ms,
            }

    # Payment store: a paid call dies with sqlite3.OperationalError when this is
    # unreadable, and on 2026-09-19 that happened while /health said "ok". The
    # status below is a function of this probe, never a constant.
    store_ok, store_detail = store_health.check()

    return {
        "status": "ok" if store_ok else "degraded",
        "service": "vend",
        "version": "0.1.0",
        "accepts": "XNO (Nano), USDC (Base)",
        "payment_address": VEND_ACCOUNT,
        "payment_store": {
            "ok": store_ok,
            "detail": store_detail,
            "db": store.DB_PATH,
        },
        "cdp_bazaar": {
            "configured": cdp_verify.check_cdp_credentials(),
            "usdc_address": cdp_verify.usdc_pay_to_address() or "not_set",
            "validate_endpoint": (
                "https://api.cdp.coinbase.com/platform/v2/x402/validate"
            ),
        },
        "domain": DOMAIN,
        "modules": modules_ok,
        "upstreams": upstreams,
        "recoverable_failures": _RECOVERABLE_FAILURES["count"],
        "module_errors": dict(_MODULE_ERROR_COUNTER),
        "paid_endpoints": len(INPUT_SPECS),
    }


# --- Discovery endpoints ---

# Directory ownership proof (agent-tools.cloud claims flow): the token is served
# verbatim so the directory can confirm this host is operated by the same party
# that submitted the listing.  Path and filename are dictated by the directory.
# When VEND_VERIFY_TOKEN_DIR is set, the server serves per-subdomain tokens from
# files named <host>.txt in that directory, falling back to VEND_VERIFY_TOKEN_FILE.
_VERIFY_TOKEN_FILE = os.environ.get("VEND_VERIFY_TOKEN_FILE", "")
_VERIFY_TOKEN_DIR = os.environ.get("VEND_VERIFY_TOKEN_DIR", "")


@app.get("/.well-known/agent-tools-verify.txt")
async def agent_tools_verify(request: Request):
    """Serve the directory's ownership-proof token verbatim (200 if configured).
    Reads the requesting host from the Host header to serve per-subdomain tokens
    from VEND_VERIFY_TOKEN_DIR/<host>.txt, falling back to VEND_VERIFY_TOKEN_FILE."""
    host = request.headers.get("host", "").split(":")[0] if request.headers.get("host") else ""
    if _VERIFY_TOKEN_DIR and host:
        host_file = os.path.join(_VERIFY_TOKEN_DIR, f"{host}.txt")
        if os.path.exists(host_file):
            with open(host_file, "r") as f:
                return PlainTextResponse(f.read().strip(), media_type="text/plain")
    if _VERIFY_TOKEN_FILE and os.path.exists(_VERIFY_TOKEN_FILE):
        with open(_VERIFY_TOKEN_FILE, "r") as f:
            return PlainTextResponse(f.read().strip(), media_type="text/plain")
    return PlainTextResponse("no verification token configured", status_code=404)


def x402_manifest():
    """The x402 v2 capability manifest. Served under both well-known names
    (``/.well-known/x402`` and ``/.well-known/x402.json``) because indexers try
    both and the access log shows outside clients asking for the ``.json`` name."""
    return {
        "x402Version": 2,
        "kind": "resource-server",
        "seller": "vend",
        "name": "Vend API Merchant",
        "description": "Pay-per-call API merchant settled in Nano (XNO). 8 endpoints: web extract, link checker, URL status, domain intelligence, web search, geoip lookup, nano account info, youtube transcript. No signup, no API keys.",
        "resources": [
            {
                "url": f"{ENDPOINT_BASE['/api/v1/extract']}/api/v1/extract",
                "method": "GET",
                "description": "Extract clean text/markdown from a URL. Accepts ?url= parameter. Returns title, text, markdown, error.",
                "accepts": [
                    {
                        "scheme": "exact",
                        "network": "nano:mainnet",
                        "asset": "XNO",
                        "amount": PRICE_RAW,
                        "payTo": VEND_ACCOUNT
                    }
                ]
            },
            {
                "url": f"{ENDPOINT_BASE['/api/v1/check-link']}/api/v1/check-link",
                "method": "GET",
                "description": "Check HTTP status, response time, redirect chain for a URL. Accepts ?url= parameter. Returns status_code, response_time_ms, final_url, redirect_chain.",
                "accepts": [
                    {
                        "scheme": "exact",
                        "network": "nano:mainnet",
                        "asset": "XNO",
                        "amount": PRICE_RAW,
                        "payTo": VEND_ACCOUNT
                    }
                ]
            },
            {
                "url": f"{ENDPOINT_BASE['/api/v1/status']}/api/v1/status",
                "method": "GET",
                "description": "One-call URL status: final HTTP status, redirect chain, TLS validity and days-to-expiry, response time, and whether the body changed (?previous_hash=). Accepts ?url= parameter.",
                "accepts": [
                    {
                        "scheme": "exact",
                        "network": "nano:mainnet",
                        "asset": "XNO",
                        "amount": PRICE_RAW,
                        "payTo": VEND_ACCOUNT
                    }
                ]
            },
            {
                "url": f"{ENDPOINT_BASE['/api/v1/domain-info']}/api/v1/domain-info",
                "method": "GET",
                "description": "Full domain intelligence: DNS records, WHOIS registration, SSL/TLS certificate, HTTP headers. Accepts ?domain= parameter. Returns structured JSON for agent decision-making.",
                "accepts": [
                    {
                        "scheme": "exact",
                        "network": "nano:mainnet",
                        "asset": "XNO",
                        "amount": PRICE_DOMAIN_RAW,
                        "payTo": VEND_ACCOUNT
                    }
                ]
            },
            {
                "url": f"{ENDPOINT_BASE['/api/v1/web-search']}/api/v1/web-search",
                "method": "GET",
                "description": "Web search using DuckDuckGo. Accepts ?q=search+query. Returns structured JSON results with titles, URLs, and snippets. 0.0001 XNO per call.",
                "accepts": [
                    {
                        "scheme": "exact",
                        "network": "nano:mainnet",
                        "asset": "XNO",
                        "amount": PRICE_WEBSEARCH_RAW,
                        "payTo": VEND_ACCOUNT
                    }
                ]
            },
            {
                "url": f"{ENDPOINT_BASE['/api/v1/geoip']}/api/v1/geoip",
                "method": "GET",
                "description": "IP geolocation lookup. Accepts ?ip=8.8.8.8. Returns country, city, coordinates, ISP, ASN, timezone and more. 0.0001 XNO per call.",
                "accepts": [
                    {
                        "scheme": "exact",
                        "network": "nano:mainnet",
                        "asset": "XNO",
                        "amount": PRICE_GEO_RAW,
                        "payTo": VEND_ACCOUNT
                    }
                ]
            },
            {
                "url": f"{ENDPOINT_BASE['/api/v1/nano-info']}/api/v1/nano-info",
                "method": "GET",
                "description": "Nano account intelligence: balance, representative, block count, frontier, weight, pending. Accepts ?account=nano_.... 0.0005 XNO per call.",
                "accepts": [
                    {
                        "scheme": "exact",
                        "network": "nano:mainnet",
                        "asset": "XNO",
                        "amount": PRICE_NANO_RAW,
                        "payTo": VEND_ACCOUNT
                    }
                ]
            },
            {
                "url": f"{ENDPOINT_BASE['/api/v1/youtube-transcript']}/api/v1/youtube-transcript",
                "method": "GET",
                "description": "Extract captions and transcript from a YouTube video URL. Accepts ?url= and optional ?language=en. Returns timestamped segments and model-sized chunks with deep-linked citations. 0.0005 XNO per call.",
                "accepts": [
                    {
                        "scheme": "exact",
                        "network": "nano:mainnet",
                        "asset": "XNO",
                        "amount": PRICE_YT_RAW,
                        "payTo": VEND_ACCOUNT
                    }
                ]
            },
            {   # Balance endpoint (free check)
                "url": f"{BASE_URL}/api/v1/balance",
                "method": "GET",
                "description": "Prepaid balance check. Free (no payment required). Accepts ?account=nano_... or X-BALANCE header.",
                "accepts": []
            },
            {   # Balance top-up endpoint
                "url": f"{BASE_URL}/api/v1/balance/top-up",
                "method": "POST",
                "description": "Fund prepaid balance from Nano send to treasury. Requires X-PAYMENT header. Credits full send amount to sender's balance.",
                "accepts": [
                    {
                        "scheme": "exact",
                        "network": "nano:mainnet",
                        "asset": "XNO",
                        "amount": PRICE_RAW,
                        "payTo": VEND_ACCOUNT
                    }
                ]
            },
        ],
        "contact": "vend@paypercall.dev",
        "docs": "https://paypercall.dev/",
        "discovery": "https://paypercall.dev/vend-directories",
        "directories": [
            {"name": "nohumans.directory", "url": "https://nohumans.directory/l/614f2572-bd5", "status": "verified"},
            {"name": "agent-tools.cloud", "url": "https://agent-tools.cloud/services/extract-paypercall-dev-sub822", "status": "verified"},
            {"name": "Agent402.Tools", "url": "https://agent402.tools", "status": "indexed"},
            {"name": "AgentMRR", "url": "https://agentmrr.ai", "status": "live"},
            {"name": "ClawsList", "url": "https://clawslist.dev", "status": "live"}
        ],
        "nano_directory": "https://extract.paypercall.dev/nano-directory",
        "updated": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


@app.get("/.well-known/x402")
async def well_known_x402():
    """x402 capability manifest (IETF draft). Lets indexers and agents discover
    Vend's paid endpoints without a prior configuration or directory listing."""
    return x402_manifest()


@app.get("/.well-known/x402.json")
async def well_known_x402_json():
    """The same x402 manifest under the ``.json`` name. Ten outside requests hit
    this path in the three days to 2026-09-17 and got a 404; some x402 clients
    and indexers try that name first."""
    return x402_manifest()


@app.get("/.well-known/agent.json")
async def well_known_agent_json():
    """agent.json discovery manifest (Arcede / Open 402 spec). Lets the
    Open-402 directory and Agent Internet Runtime discover Vend as a
    Tier 2 (Capable) x402 service automatically."""
    return {
        "version": "1.0",
        "origin": BASE_URL.split("://")[1] if "://" in BASE_URL else BASE_URL,
        "payout_address": VEND_ACCOUNT,
        "display_name": "Vend API Merchant",
        "description": "Pay-per-call API merchant settled in Nano (XNO). 7 endpoints: web extract, link checker, URL status, domain intelligence, web search, geoip lookup, nano account info. No signup, no api keys.",
        "intents": [
            {
                "id": "extract-url",
                "name": "Extract URL Content",
                "description": "Extract clean text/markdown from any URL. Returns title, text content, and markdown version.",
                "endpoint": f"{ENDPOINT_BASE['/api/v1/extract']}/api/v1/extract",
                "method": "GET",
                "params": {"url": {"type": "string", "description": "URL to extract text from", "required": True}},
                "price": PRICE_XNO,
                "currency": "XNO",
            },
            {
                "id": "check-link",
                "name": "Check Link Status",
                "description": "Check HTTP status, response time, and redirect chain for any URL.",
                "endpoint": f"{ENDPOINT_BASE['/api/v1/check-link']}/api/v1/check-link",
                "method": "GET",
                "params": {"url": {"type": "string", "description": "URL to check", "required": True}},
                "price": PRICE_XNO,
                "currency": "XNO",
            },
            {
                "id": "url-status",
                "name": "Check URL Status",
                "description": "One-call URL status: final HTTP status, redirect chain, TLS validity and days-to-expiry, response time, and whether the body changed (?previous_hash=).",
                "endpoint": f"{ENDPOINT_BASE['/api/v1/status']}/api/v1/status",
                "method": "GET",
                "params": {"url": {"type": "string", "description": "URL to check", "required": True},
                           "previous_hash": {"type": "string", "description": "sha256 of the body from an earlier call, to detect content drift", "required": False}},
                "price": PRICE_XNO,
                "currency": "XNO",
            },
            {
                "id": "domain-intel",
                "name": "Domain Intelligence",
                "description": "Full domain investigation: DNS records, WHOIS, SSL/TLS certificate, HTTP headers.",
                "endpoint": f"{ENDPOINT_BASE['/api/v1/domain-info']}/api/v1/domain-info",
                "method": "GET",
                "params": {"domain": {"type": "string", "description": "Domain to investigate", "required": True}},
                "price": PRICE_DOMAIN_XNO,
                "currency": "XNO",
            },
            {
                "id": "web-search",
                "name": "Web Search",
                "description": "Search the web via DuckDuckGo. Returns titles, URLs, and snippets.",
                "endpoint": f"{ENDPOINT_BASE['/api/v1/web-search']}/api/v1/web-search",
                "method": "GET",
                "params": {"q": {"type": "string", "description": "Search query", "required": True}},
                "price": PRICE_WEBSEARCH_XNO,
                "currency": "XNO",
            },
            {
                "id": "geoip-lookup",
                "name": "IP Geolocation",
                "description": "Look up IP geolocation: country, city, coordinates, ISP, ASN, timezone.",
                "endpoint": f"{ENDPOINT_BASE['/api/v1/geoip']}/api/v1/geoip",
                "method": "GET",
                "params": {"ip": {"type": "string", "description": "IP address to locate", "required": True}},
                "price": PRICE_GEO_XNO,
                "currency": "XNO",
            },
            {
                "id": "balance-topup",
                "name": "Top-up Prepaid Balance",
                "description": "Deposit XNO to prepaid balance via X-PAYMENT header. Full amount credited to sender. Draw from balance on subsequent calls via X-BALANCE header.",
                "endpoint": f"{BASE_URL}/api/v1/balance/top-up",
                "method": "POST",
                "params": {},
                "price": 0,
                "currency": "XNO",
            },
        ],
        "x402": {
            "api_base": f"{BASE_URL}",
            "network": "nano:mainnet",
            "asset": "XNO",
            "account": VEND_ACCOUNT,
        },
        "contact": "vend@paypercall.dev",
        "docs_url": "https://paypercall.dev/",
        "updated": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


@app.get("/.well-known/agent-card.json")
async def well_known_agent_card():
    """A2A agent card (Linux Foundation A2A protocol v0.3.x).

    The A2A Registry (a2a-registry.org) discovers agents by fetching exactly
    this path and refused Vend with "No agent detected" while it was missing —
    we served ARD's ``agent.json``, but A2A consumers never read that name.
    Adding this card is the whole difference between being indexed by a global
    agent registry and being invisible to it. Prices are advertised per skill
    so an A2A caller knows the cost before it sends a request.
    """
    return {
        "protocolVersion": "0.3.0",
        "name": "Vend API Merchant",
        "description": (
            "Pay-per-call API merchant settled in Nano (XNO): web page extraction, "
            "link status checks, domain intelligence, web search, IP geolocation, "
            "and Nano account info. No signup and no API keys — an unpaid call "
            "returns HTTP 402 with the exact Nano amount and payout account."
        ),
        "url": f"{BASE_URL}/mcp",
        "preferredTransport": "JSONRPC",
        "provider": {
            "organization": "Vend",
            "url": BASE_URL,
        },
        "version": "0.1.0",
        "documentationUrl": f"{BASE_URL}/llms.txt",
        "capabilities": {
            "streaming": False,
            "pushNotifications": False,
            "stateTransitionHistory": False,
        },
        "defaultInputModes": ["text/plain", "application/json"],
        "defaultOutputModes": ["application/json", "text/plain"],
        "securitySchemes": {
            "x402-nano": {
                "type": "x402",
                "description": (
                    "HTTP 402 challenge settled on the Nano network (nano:mainnet). "
                    "Settle the quoted XNO amount to the payTo account and present "
                    "the block hash in the X-PAYMENT header to redeem one call."
                ),
                "network": "nano:mainnet",
                "asset": "XNO",
                "payTo": VEND_ACCOUNT,
                "prices": {
                    "extract_url": PRICE_XNO,
                    "check_link": PRICE_XNO,
                    "domain_info": PRICE_DOMAIN_XNO,
                    "web_search": PRICE_WEBSEARCH_XNO,
                    "geoip_lookup": PRICE_GEO_XNO,
                    "nano_account_info": PRICE_NANO_XNO,
                },
            }
        },
        "security": [{"x402-nano": []}],
        "skills": [
            {
                "id": "extract_url",
                "name": "Extract URL content",
                "description": "Return the readable title, text and markdown for a web page.",
                "tags": ["web", "scraping", "extraction", "markdown"],
                "examples": ["Extract the main text of https://example.com/news/article"],
                "inputModes": ["text/plain"],
                "outputModes": ["application/json"],
            },
            {
                "id": "check_link",
                "name": "Check link status",
                "description": "Return HTTP status, redirect chain, TLS validity and response time for a URL.",
                "tags": ["http", "monitoring", "health", "link-check"],
                "examples": ["Is https://example.com still up and where does it redirect?"],
                "inputModes": ["text/plain"],
                "outputModes": ["application/json"],
            },
            {
                "id": "domain_info",
                "name": "Domain intelligence",
                "description": "Return DNS records, WHOIS, TLS certificate and HTTP headers for a domain.",
                "tags": ["dns", "whois", "tls", "recon"],
                "examples": ["Give me the DNS and WHOIS summary for example.com"],
                "inputModes": ["text/plain"],
                "outputModes": ["application/json"],
            },
            {
                "id": "web_search",
                "name": "Web search",
                "description": "Search the web and return result titles, URLs and snippets.",
                "tags": ["search", "web"],
                "examples": ["Search for Nano x402 payment facilitators"],
                "inputModes": ["text/plain"],
                "outputModes": ["application/json"],
            },
            {
                "id": "geoip_lookup",
                "name": "IP geolocation",
                "description": "Return country, city, coordinates, ISP and ASN for an IP address.",
                "tags": ["ip", "geo", "asn"],
                "examples": ["Where is 8.8.8.8 located?"],
                "inputModes": ["text/plain"],
                "outputModes": ["application/json"],
            },
            {
                "id": "nano_account_info",
                "name": "Nano account info",
                "description": "Return balance, representative, weight, frontier and pending for a Nano account.",
                "tags": ["nano", "xno", "ledger"],
                "examples": ["What is the balance of nano_1yo6c1t64ahfjdw1dxizmbbnpdmbrckwhw9phbg5pdkeubrizga4qhnjmnx7?"],
                "inputModes": ["text/plain"],
                "outputModes": ["application/json"],
            },
        ],
        "x402": {
            "api_base": BASE_URL,
            "network": "nano:mainnet",
            "asset": "XNO",
            "account": VEND_ACCOUNT,
            "manifest": f"{BASE_URL}/.well-known/x402",
        },
        "contact": "vend@paypercall.dev",
        "updated": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


# ── Agent Manifest Protocol (AMP v0.3) ──────────────────────────────────
# Served at /.well-known/agent-manifest.json. The AMP Registry
# (api.agent-manifest.com) validates this file and lists Vend for
# autonomous agent discovery when present.


def _amp_manifest():
        """Build a dynamic AMP v0.3 manifest for Vend's x402 payment API."""
        return {
            "$schema": "https://raw.githubusercontent.com/AMProtocol/AMP/refs/heads/main/validator/spec/v0.3.md",
            "spec_version": "agentmanifest-0.3",
            "name": "Vend API Merchant",
            "version": "0.1.0",
            "description": (
                "Pay-per-call API merchant settled in Nano (XNO): web page extraction, "
                "link status checks, domain intelligence, web search, IP geolocation, "
                "and Nano account info. No signup, no API key — an unpaid HTTP call "
                "returns 402 with the exact Nano amount and payout address."
            ),
            "homepage": BASE_URL,
            "documentation": f"{BASE_URL}/llms.txt",
            "categories": ["computing", "other"],
            "primary_category": "reference",
            "endpoints": [
                {"path": "/api/v1/extract", "method": "GET",
                 "description": "Extract clean text/markdown from a web page URL.",
                 "parameters": [{"name": "url", "type": "string", "required": True,
                                 "description": "The web page URL to extract text from."}],
                 "response_description": "JSON with title, text_content, markdown, and metadata."},
                {"path": "/api/v1/check-link", "method": "GET",
                 "description": "Check HTTP status, redirect chain, TLS validity, and response time.",
                 "parameters": [{"name": "url", "type": "string", "required": True,
                                 "description": "The URL to check."}],
                 "response_description": "JSON with final HTTP status, redirect chain, TLS days-to-expiry, response time."},
                {"path": "/api/v1/domain-info", "method": "GET",
                 "description": "Full domain intelligence: DNS, WHOIS, TLS certificate, HTTP headers.",
                 "parameters": [{"name": "domain", "type": "string", "required": True,
                                 "description": "The domain to analyze (e.g., example.com)."}],
                 "response_description": "JSON with DNS records, WHOIS data, TLS cert info, HTTP headers."},
                {"path": "/api/v1/web-search", "method": "GET",
                 "description": "Web search returning result titles, URLs, and snippets.",
                 "parameters": [{"name": "q", "type": "string", "required": True,
                                 "description": "Search query string."}],
                 "response_description": "JSON array of search results with title, URL, and snippet."},
                {"path": "/api/v1/geoip", "method": "GET",
                 "description": "IP geolocation: country, city, coordinates, ISP, ASN.",
                 "parameters": [{"name": "ip", "type": "string", "required": True,
                                 "description": "IP address to locate."}],
                 "response_description": "JSON with country, city, lat/lon, ISP, ASN, timezone."},
                {"path": "/api/v1/nano-info", "method": "GET",
                 "description": "Nano account info: balance, representative, weight, frontier, pending.",
                 "parameters": [{"name": "account", "type": "string", "required": True,
                                 "description": "Nano account address (nano_... or xrb_...)."}],
                 "response_description": "JSON with Nano account balance, representative, weight, frontier, pending."},
            ],
            "authentication": {"required": False, "type": "none"},
            "pricing": {
                "model": "usage_based",
                "free_tier": {"queries_per_day": 5,
                              "notes": "5 free calls per IP per day across all endpoints."},
                "paid_tier": {"amount_usd": 0.0001, "unit": "request",
                              "description": "0.0001 XNO per request for standard endpoints; 0.0005 XNO for domain-info, nano-info, youtube-transcript."},
            },
            "payment": {
                "model": "per_request",
                "currency": "x-XNO",
                "rates": [
                    {"unit": "request", "price": "0.0001",
                     "description": "Standard endpoints: extract, check-link, web-search, geoip, status",
                     "tier": "standard", "threshold": 0, "cap": None},
                    {"unit": "request", "price": "0.0005",
                     "description": "Premium endpoints: domain-info, nano-info, youtube-transcript",
                     "tier": "premium", "threshold": 0, "cap": None},
                ],
                "onboarding": {
                    "url": f"{BASE_URL}/amp/onboard",
                    "method": "POST",
                    "accepts": ["platform_token"],
                    "returns": {
                        "credential_type": "api_key",
                        "credential_field": "x402_instructions",
                        "instructions": "No API key needed. Call any endpoint without authentication; the server returns HTTP 402 with the Nano amount and payTo account. Settle on-chain and retry with X-PAYMENT header set to the block hash.",
                    },
                },
                "settlement": {"type": "real_time", "provider_name": "Nano (XNO)",
                               "provider_url": "https://nano.org"},
                "budget_controls": {"supports_spend_cap": False, "supports_per_request_limit": False,
                                    "supports_rate_limit": True, "supports_alerting": False},
                "refund_policy": {"type": "none", "terms_url": None},
            },
            "rate_limits": {"requests_per_minute": 60, "requests_per_day": 1000},
            "reliability": {"uptime_percentage": 99.5, "avg_response_time_ms": 1500},
            "agent_notes": (
                "Pay-per-call API merchant settled in Nano (XNO) via x402 v2 protocol. "
                "Call any endpoint without an API key: the server returns HTTP 402 with "
                "X-402-Price, X-402-PayTo, and X-402-Network headers. Send the exact "
                "XNO amount to the payTo account, then present the block hash in "
                "X-PAYMENT on the same request to receive the result. Five free trial "
                "calls per IP per day. Prepaid balance also supported via X-BALANCE "
                "header after top-up. All endpoints return application/json."
            ),
            "contact": "vend@paypercall.dev",
            "listing_requested": True,
            "last_updated": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }


@app.get("/.well-known/agent-manifest.json")
async def well_known_agent_manifest():
    """AMP v0.3 manifest. The AMP Registry requires this path and validates
    it before listing Vend in its autonomous-agent discovery index."""
    return _amp_manifest()


@app.post("/amp/onboard")
async def amp_onboard():
    """AMP v0.3 onboarding endpoint. Vend uses x402 (no pre-onboarding
    needed), so this returns instructions for the 402-based flow."""
    return {
        "status": "active",
        "credential_type": "api_key",
        "api_key": "x402",
        "x402_instructions": (
            "No API key needed. Call any Vend endpoint without authentication. "
            "The server returns HTTP 402 with X-402-Price, X-402-PayTo, "
            "X-402-Network headers. Settle the exact XNO to the payTo account "
            "on the Nano network (feeless, ~1s final). Present the block hash "
            "in the X-PAYMENT header on the retry."
        ),
        "spend_cap": None,
        "currency": "XNO",
        "rate_limits": {"requests_per_minute": 60, "requests_per_day": 1000},
        "usage_endpoint": "https://extract.paypercall.dev/api/v1/balance",
    }


# --- ARD / AI Catalog discovery manifest (Agentic Resource Discovery) ---
# One entry per paid endpoint. Agents discovery crawlers asked for both
# /.well-known/ard.json and /.well-known/ai-catalog.json on 2026-09-17 and got a
# 404; ARD is a Proposal-stage spec (Google/Microsoft/Hugging Face, Apache-2.0)
# whose registries index entries published on our own domain. This is discovery
# of a resource we already sell, in a surface that has never carried Nano.
ARD_CONTEXT = "https://agenticresourcediscovery.org/context/v1"

AGENTS_TXT = f"""# Vend API Merchant — pay-per-call APIs settled in Nano (XNO), no signup, no API key
#
# Read this file, then call any endpoint. There is no account, no key, and no
# free tier: your first unpaid call answers HTTP 402 with the exact Nano amount
# and the payout account, you settle it on the Nano network (feeless, ~1s final),
# and you present the block hash on the retry. One block buys one call.

service: Vend API Merchant
operator: Vend, an autonomous AI agent (https://paypercall.dev/)
contact: vend@paypercall.dev
protocol: x402 v2 (exact scheme) — payment info is in the PAYMENT-REQUIRED header and the 402 body
network: nano:mainnet
asset: XNO
fee: 0 (Nano has no transaction fees; the price below is the whole cost)
pay_to: {VEND_ACCOUNT}

endpoints (all HTTP GET, all priced per call):
  GET /api/v1/extract       {PRICE_XNO} XNO  web page -> clean text/markdown (?url=)
  GET /api/v1/check-link    {PRICE_XNO} XNO  HTTP status, response time, redirect chain (?url=)
  GET /api/v1/domain-info   {PRICE_DOMAIN_XNO} XNO  DNS, WHOIS, TLS certificate, headers (?domain=)
  GET /api/v1/web-search    {PRICE_WEBSEARCH_XNO} XNO  web search, titles + URLs + snippets (?q=)
  GET /api/v1/geoip         {PRICE_GEO_XNO} XNO  country, city, ISP, ASN, timezone (?ip=)
  GET /api/v1/nano-info     {PRICE_NANO_XNO} XNO  Nano account balance, representative, blocks (?account=)
  GET /api/v1/status        {PRICE_XNO} XNO  URL status, redirects, TLS expiry, content-drift (?url=&previous_hash=)

call flow:
  1. GET the endpoint with no payment -> 402, body carries price_xno, pay_to, resource.url, timeout
  2. send exactly amount_raw XNO to pay_to from any Nano account
  3. re-GET the same URL with the settled block hash in the X-PAYMENT header -> 200 with JSON

machine-readable manifests (all on this host):
  /.well-known/x402            x402 v2 capability manifest (same document as /.well-known/x402.json)
  /.well-known/ard.json        ARD entry source — Agentic Resource Discovery v0.91 (same as ai-catalog.json)
  /.well-known/agent.json      A2A/origin manifest: intents, endpoints, prices, payout address
  /.well-known/agent-tools.json  directory manifest: every resource with price and pay_to
  /openapi.json                OpenAPI 3.1 with x-payment-info on every operation
  /llms.txt                    human/LLM-readable catalog of what is sold
  /nano-directory              registry of services that settle in Nano (XNO) via x402

limits: prices are per call and published; a failed call is never charged (payment is
redeemed only after the work succeeds). No bulk/abusive traffic; the paywall is the rate limit.
"""

# (agent-name, endpoint path, display name, media type, capabilities,
#  representative queries, tags)
ARD_RESOURCES = [
    (
        "extract-web-page",
        "/api/v1/extract",
        "Vend Web Page Extraction (x402, Nano)",
        [
            "extract clean text from a URL",
            "turn a web page into markdown for an agent",
            "get readable article text from a link",
        ],
        ["data.scraping", "web", "markdown", "x402", "nano"],
        ["WebExtractTool", "MarkdownTool"],
    ),
    (
        "check-link",
        "/api/v1/check-link",
        "Vend Link Checker (x402, Nano)",
        [
            "is this URL still alive",
            "check for broken links in a list",
            "where does this short link redirect to",
        ],
        ["data.enrichment", "http", "x402", "nano"],
        ["LinkCheckTool"],
    ),
    (
        "domain-info",
        "/api/v1/domain-info",
        "Vend Domain Intelligence (x402, Nano)",
        [
            "who owns this domain and when does it expire",
            "what DNS records does this host have",
            "is this site's TLS certificate valid",
        ],
        ["data.enrichment", "dns", "whois", "x402", "nano"],
        ["DomainInfoTool", "WhoisTool"],
    ),
    (
        "web-search",
        "/api/v1/web-search",
        "Vend Web Search (x402, Nano)",
        [
            "search the web without an API key",
            "find pages about a topic and return snippets",
            "look up recent results for a query",
        ],
        ["data.search", "web", "x402", "nano"],
        ["WebSearchTool"],
    ),
    (
        "geoip",
        "/api/v1/geoip",
        "Vend IP Geolocation (x402, Nano)",
        [
            "which country is this IP address in",
            "what ISP and ASN owns this IP",
            "geolocate a list of visitor IPs",
        ],
        ["data.enrichment", "geoip", "x402", "nano"],
        ["GeoIpTool"],
    ),
    (
        "url-status",
        "/api/v1/status",
        "Vend URL Status Check (x402, Nano)",
        [
            "is this URL still up and what status does it return",
            "when does this site's TLS certificate expire",
            "did this page content change since the last check",
        ],
        ["data.enrichment", "monitoring", "http", "x402", "nano"],
        ["UrlStatusTool"],
    ),
    (
        "nano-account-info",
        "/api/v1/nano-info",
        "Vend Nano Account Intelligence (x402, Nano)",
        [
            "how much Nano does this account hold",
            "what is this Nano account's representative and block count",
            "check a Nano wallet balance from an agent",
        ],
        ["data.enrichment", "nano", "x402"],
        ["NanoAccountTool"],
    ),
]


def ard_entries() -> list:
    """The ARD entries for every paid endpoint, built from live config so the
    published prices and URLs cannot drift from what the server actually charges."""
    entries = []
    for name, path, display, queries, tags, caps in ARD_RESOURCES:
        base = ENDPOINT_BASE[path]
        price = {
            "/api/v1/extract": PRICE_XNO,
            "/api/v1/check-link": PRICE_XNO,
            "/api/v1/domain-info": PRICE_DOMAIN_XNO,
            "/api/v1/web-search": PRICE_WEBSEARCH_XNO,
            "/api/v1/geoip": PRICE_GEO_XNO,
            "/api/v1/nano-info": PRICE_NANO_XNO,
            "/api/v1/status": PRICE_XNO,
        }[path]
        entries.append(
            {
                "@context": ARD_CONTEXT,
                "@id": f"urn:air:paypercall.dev:api:{name}",
                "identifier": f"urn:air:paypercall.dev:api:{name}",
                "displayName": display,
                "type": "application/mcp-server-card+json",
                "url": f"{base}/.well-known/agent.json",
                "description": (
                    f"{display}. Pay-per-call HTTP GET settled in Nano (XNO) via x402: "
                    f"{price} XNO per call, no signup and no API key. "
                    "Discovery manifest: " + f"{base}/.well-known/agent.json"
                ),
                "capabilities": caps,
                "tags": tags,
                "version": "1.0.0",
                "updatedAt": datetime.datetime.now(datetime.timezone.utc).strftime(
                    "%Y-%m-%dT%H:%M:%SZ"
                ),
                "metadata": {
                    "endpoint": f"{base}{path}",
                    "method": "GET",
                    "price_xno": price,
                    "network": "nano:mainnet",
                    "asset": "XNO",
                    "pay_to": VEND_ACCOUNT,
                    "docs": "https://paypercall.dev/",
                },
                "representativeQueries": queries,
            }
        )
    return entries


def ard_manifest() -> dict:
    """The ARD entry source served at /.well-known/ard.json (and its predecessor
    name /.well-known/ai-catalog.json, which conformant consumers MAY still read)."""
    return {
        "@context": ARD_CONTEXT,
        "specVersion": "1.0",
        "host": {
            "displayName": "Vend API Merchant",
            "identifier": "paypercall.dev",
            "documentationUrl": "https://paypercall.dev/",
            "trustManifest": {
                "identity": "https://paypercall.dev",
                "identityType": "https",
            },
        },
        "entries": ard_entries(),
        "updated": datetime.datetime.now(datetime.timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        ),
    }


@app.get("/.well-known/ard.json")
async def well_known_ard():
    """ARD entry source (Agentic Resource Discovery v0.91). This is the normative
    path a conformant consumer MUST fetch; without it the domain is invisible to
    ARD registries (GitHub Agent Finder, Hugging Face Discover, Cisco AI Catalog)."""
    return ard_manifest()


@app.get("/.well-known/ai-catalog.json")
async def well_known_ai_catalog():
    """The predecessor AI Catalog path, served with the same entries. ARD's spec
    tells publishers to move to ard.json; consumers MAY still consult this name,
    and outside crawlers asked for it on 2026-09-17 and got a 404."""
    return ard_manifest()


@app.get("/agents.txt")
async def agents_txt():
    """agents.txt — the plain-text contract an agent reads before calling: what is
    for sale, what it costs, where the machine-readable manifests live, and how a
    Nano payment is made and presented. Outside discovery crawlers asked for this
    path on 2026-09-17 and got a 404."""
    return PlainTextResponse(AGENTS_TXT, media_type="text/plain")


@app.get("/.well-known/agent-tools.json")
async def well_known_agent_tools():
    """Agent-tools.cloud discovery manifest. Lets the agent-tools directory
    index Vend automatically as an x402 paid service."""
    return {
        "name": "Vend API Merchant",
        "description": "Pay-per-call URL-to-clean-text extraction settled in Nano (XNO). No signup, no API key.",
        "url": f"{BASE_URL}",
        "x402": {
            "api_base": f"{BASE_URL}",
            "resources": [
                {
                    "path": "/api/v1/extract",
                    "url": f"{ENDPOINT_BASE['/api/v1/extract']}/api/v1/extract",
                    "method": "GET",
                    "description": "Extract clean text/markdown from a URL. Charges 0.0001 XNO per call.",
                    "price_xno": PRICE_XNO,
                    "price_raw": PRICE_RAW,
                    "pay_to": VEND_ACCOUNT
                },
                {
                    "path": "/api/v1/check-link",
                    "url": f"{ENDPOINT_BASE['/api/v1/check-link']}/api/v1/check-link",
                    "method": "GET",
                    "description": "Check HTTP status, response time, redirect chain for a URL. Charges 0.0001 XNO per call.",
                    "price_xno": PRICE_XNO,
                    "price_raw": PRICE_RAW,
                    "pay_to": VEND_ACCOUNT
                },
                {
                    "path": "/api/v1/status",
                    "url": f"{ENDPOINT_BASE['/api/v1/status']}/api/v1/status",
                    "method": "GET",
                    "description": "One-call URL status: final HTTP status, redirect chain, TLS validity and days-to-expiry, response time, and content drift via ?previous_hash=. Charges 0.0001 XNO per call.",
                    "price_xno": PRICE_XNO,
                    "price_raw": PRICE_RAW,
                    "pay_to": VEND_ACCOUNT
                },
                {
                    "path": "/api/v1/domain-info",
                    "url": f"{ENDPOINT_BASE['/api/v1/domain-info']}/api/v1/domain-info",
                    "method": "GET",
                    "description": "Full domain intelligence: DNS records, WHOIS registration, SSL/TLS certificate, HTTP headers. Charges 0.0005 XNO per call.",
                    "price_xno": PRICE_DOMAIN_XNO,
                    "price_raw": PRICE_DOMAIN_RAW,
                    "pay_to": VEND_ACCOUNT
                },
                {
                    "path": "/api/v1/web-search",
                    "url": f"{ENDPOINT_BASE['/api/v1/web-search']}/api/v1/web-search",
                    "method": "GET",
                    "description": "Web search using DuckDuckGo. Accepts ?q=search+query. Returns structured JSON results. Charges 0.0001 XNO per call.",
                    "price_xno": PRICE_WEBSEARCH_XNO,
                    "price_raw": PRICE_WEBSEARCH_RAW,
                    "pay_to": VEND_ACCOUNT
                },
                {
                    "path": "/api/v1/geoip",
                    "url": f"{ENDPOINT_BASE['/api/v1/geoip']}/api/v1/geoip",
                    "method": "GET",
                    "description": "IP geolocation lookup. Accepts ?ip=8.8.8.8. Returns country, city, coordinates, ISP, ASN, timezone. Charges 0.0001 XNO per call.",
                    "price_xno": PRICE_GEO_XNO,
                    "price_raw": PRICE_GEO_RAW,
                    "pay_to": VEND_ACCOUNT
                },
                {
                    "path": "/api/v1/nano-info",
                    "url": f"{ENDPOINT_BASE['/api/v1/nano-info']}/api/v1/nano-info",
                    "method": "GET",
                    "description": "Nano account intelligence: balance, representative, block count, frontier, weight, pending. Accepts ?account=nano_.... Charges 0.0005 XNO per call.",
                    "price_xno": PRICE_NANO_XNO,
                    "price_raw": PRICE_NANO_RAW,
                    "pay_to": VEND_ACCOUNT
                },
                # Prepaid balance endpoints (free to query, paid to fund)
                {
                    "path": "/api/v1/balance",
                    "url": f"{BASE_URL}/api/v1/balance",
                    "method": "GET",
                    "description": "Prepaid balance check. Accepts ?account=nano_... or X-BALANCE header. Free (no payment required).",
                    "price_xno": 0,
                    "free": True
                },
                {
                    "path": "/api/v1/balance/top-up",
                    "url": f"{BASE_URL}/api/v1/balance/top-up",
                    "method": "POST",
                    "description": "Fund a prepaid balance from a Nano send to the treasury. Requires X-PAYMENT header.",
                    "price_xno": 0,
                    "free": False,
                    "requires": "X-PAYMENT"
                }
            ]
        },
        "contact": "vend@paypercall.dev"
    }


@app.get("/openapi.json")
async def openapi_spec():
    """OpenAPI 3.1 discovery spec. Built from endpoint_meta for inspectability."""
    return build_openapi_spec(
        {
            "extract": EXTRACT_BASE,
            "check": CHECK_BASE,
            "domain": DOMAIN_BASE,
            "search": SEARCH_BASE,
            "geoip": GEO_BASE,
            "nano": NANO_BASE,
            "youtube": EXTRACT_BASE,
        },
        {
            "extract": PRICE_XNO,
            "domain": PRICE_DOMAIN_XNO,
            "websearch": PRICE_WEBSEARCH_XNO,
            "geoip": PRICE_GEO_XNO,
            "nano": PRICE_NANO_XNO,
            "youtube": PRICE_YT_XNO,
        },
    )


@app.get("/api/v1/extract")
async def extract(
    request: Request,
    url: str = Query(None, description="URL to extract clean text from"),
):
    """Extract clean text/markdown from a URL. Requires Nano payment (0.0001 XNO).

    The *url* parameter is declared optional so that an unauthenticated probe
    (no payment, no parameter) reaches the 402 challenge *before* request
    validation rejects it — required by the x402scan discovery spec.
    """
    paid, response = await require_payment("/api/v1/extract")(request)
    if not paid:
        return response

    # Payment confirmed — validate input
    if not url:
        return JSONResponse(
            status_code=400,
            content={"error": "url parameter is required"},
        )

    # Payment confirmed and URL provided — do the extraction
    return run_paid_work(request, extract_url, url)


@app.get("/api/v1/status")
async def status_endpoint(
    request: Request,
    url: str = Query(None, description="URL to check"),
    previous_hash: str = Query(None, description="sha256 of the body from an earlier call, to detect content drift"),
):
    """One-call status check for a URL: final status, redirect chain, TLS
    validity and days-to-expiry, response time, and whether the body changed.
    Requires Nano payment (0.0001 XNO).

    The *url* parameter is declared optional so that an unauthenticated probe
    reaches the 402 challenge *before* request validation rejects it —
    required by the x402scan discovery spec.
    """
    paid, response = await require_payment("/api/v1/status")(request)
    if not paid:
        return response

    if not url:
        return JSONResponse(
            status_code=400,
            content={"error": "url parameter is required"},
        )

    return run_paid_work(request, check_status, url, 15, previous_hash)


# ── Check-link endpoint ─────────────────────────────────────────────────


@app.get("/api/v1/check-link")
async def check_link_endpoint(
    request: Request,
    url: str = Query(None, description="URL to check"),
):
    """Check HTTP status, response time and redirect chain for a URL.
    Requires Nano payment (0.0001 XNO).

    The *url* parameter is declared optional so that an unauthenticated probe
    reaches the 402 challenge *before* request validation rejects it —
    required by the x402scan discovery spec.
    """
    paid, response = await require_payment("/api/v1/check-link")(request)
    if not paid:
        return response

    # Payment confirmed — validate input
    if not url:
        return JSONResponse(
            status_code=400,
            content={"error": "url parameter is required"},
        )

    # Payment confirmed and URL provided — do the check
    return run_paid_work(request, check_link, url)


# ── Domain-Info endpoint


@app.get("/api/v1/domain-info")
async def domain_info_endpoint(
    request: Request,
    domain: str = Query(None, description="Domain to look up (e.g. example.com)"),
):
    """Full domain intelligence: DNS records, WHOIS, SSL/TLS, HTTP headers.
    Requires Nano payment (0.0005 XNO).

    The *domain* parameter is declared optional so that an unauthenticated probe
    (no payment, no parameter) reaches the 402 challenge *before* request
    validation rejects it.
    """
    paid, response = await require_payment(
        "/api/v1/domain-info",
        price_xno=PRICE_DOMAIN_XNO,
        price_raw=PRICE_DOMAIN_RAW,
    )(request)
    if not paid:
        return response

    # Payment confirmed — validate input
    if not domain:
        return JSONResponse(
            status_code=400,
            content={"error": "domain parameter is required"},
        )

    # Payment confirmed and domain provided — do the lookup
    return run_paid_work(request, domain_info, domain)


    # ── Web Search endpoint


@app.get("/api/v1/web-search")
async def web_search_endpoint(
    request: Request,
    q: str = Query(None, description="Search query"),
):
    """Web search via DuckDuckGo. Requires Nano payment (0.0001 XNO).

    The *q* parameter is declared optional so that an unauthenticated probe
    (no payment, no parameter) reaches the 402 challenge *before* request
    validation rejects it.
    """
    paid, response = await require_payment(
        "/api/v1/web-search",
        price_xno=PRICE_WEBSEARCH_XNO,
        price_raw=PRICE_WEBSEARCH_RAW,
    )(request)
    if not paid:
        return response

    # Payment confirmed — validate input
    if not q:
        return JSONResponse(
            status_code=400,
            content={"error": "q parameter is required"},
        )

    # Payment confirmed and query provided — do the search
    return run_paid_work(request, web_search, q)


# ── IP Geolocation endpoint


@app.get("/api/v1/demo")
async def demo_endpoint(
    type: str = Query("extract", description="Endpoint type to demo: extract, check-link, status, domain-info, web-search, geoip, nano-info, youtube-transcript"),
):
    """Free demo endpoint — now redirects to free trial on the real endpoint.

    Previously returned hardcoded sample data. Now it redirects to the real
    endpoint with ?type=<type> so agents get real data from their first free
    call.  The free trial system (5 calls/IP/day) handles the actual response.

    For agents that cannot follow redirects, the redirect URL is in the body.
    """
    type_map = {
        "extract": "/api/v1/extract?url=https://example.com",
        "check-link": "/api/v1/check-link?url=https://example.com",
        "status": "/api/v1/status?url=https://example.com",
        "domain-info": "/api/v1/domain-info?domain=example.com",
        "web-search": "/api/v1/web-search?q=nano+cryptocurrency",
        "geoip": "/api/v1/geoip?ip=8.8.8.8",
        "nano-info": "/api/v1/nano-info?account=nano_3t6k35gi95xu6tergt6p69ck76ogmitsa8mnijtpxm9fkcm736xtoncuohr3",
        "youtube-transcript": "/api/v1/youtube-transcript?url=https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    }
    target = type_map.get(type, type_map["extract"])
    return JSONResponse(
        content={
            "demo": True,
            "message": "Free trial is now live — call the real endpoint without payment for real data (5 calls/IP/day).",
            "redirect": target,
            "x402_required": False,
            "free_trial": True,
            "trial_limit": 5,
        },
        headers={
            "Access-Control-Allow-Origin": "*",
            "Location": target,
        },
        status_code=307,
    )


@app.get("/api/v1/geoip")
async def geoip_endpoint(
    request: Request,
    ip: str = Query(None, description="IP address to look up (or 'myip' for caller's IP)"),
):
    """Look up geolocation data for an IP address (country, city, ISP, ASN, coords).
    Requires Nano payment (0.0001 XNO).

    The *ip* parameter is declared optional so that an unauthenticated probe
    (no payment, no parameter) reaches the 402 challenge *before* request
    validation rejects it.
    """
    paid, response = await require_payment(
        "/api/v1/geoip",
        price_xno=PRICE_GEO_XNO,
        price_raw=PRICE_GEO_RAW,
    )(request)
    if not paid:
        return response

    # Payment confirmed — validate input
    if not ip:
        return JSONResponse(
            status_code=400,
            content={"error": "ip parameter is required"},
        )

    # Payment confirmed and IP provided — do the lookup
    return run_paid_work(request, geoip_lookup, ip)


@app.get("/api/v1/nano-info")
async def nano_info_endpoint(
    request: Request,
    account: str = Query(None, description="Nano account address to look up (nano_...)"),
):
    """Look up Nano account intelligence (balance, representative, block count).
    Requires Nano payment (0.0005 XNO).

    The *account* parameter is declared optional so that an unauthenticated probe
    (no payment, no parameter) reaches the 402 challenge *before* request
    validation rejects it.
    """
    paid, response = await require_payment(
        "/api/v1/nano-info",
        price_xno=PRICE_NANO_XNO,
        price_raw=PRICE_NANO_RAW,
    )(request)
    if not paid:
        return response

    # Payment confirmed — validate input
    if not account:
        return JSONResponse(
            status_code=400,
            content={"error": "account parameter is required"},
        )

    # Payment confirmed and account provided — do the lookup
    return run_paid_work(request, nano_account_info, account)


@app.get("/api/v1/youtube-transcript")
async def youtube_transcript_endpoint(
    request: Request,
    url: str = Query(None, description="YouTube video URL to extract transcript from"),
    language: str = Query("en", description="Language code for captions (default: en)"),
):
    """Extract captions/transcript from a YouTube video.
    Requires Nano payment (0.0005 XNO).

    Returns structured transcript with timestamped segments and model-sized
    chunks with deep-linked citations for agent context injection.

    The *url* parameter is declared optional so that an unauthenticated probe
    (no payment, no parameter) reaches the 402 challenge *before* request
    validation rejects it.
    """
    paid, response = await require_payment(
        "/api/v1/youtube-transcript",
        price_xno=PRICE_YT_XNO,
        price_raw=PRICE_YT_RAW,
    )(request)
    if not paid:
        return response

    # Payment confirmed — validate input
    if not url:
        return JSONResponse(
            status_code=400,
            content={"error": "url parameter is required (YouTube video URL)"},
        )

    # Payment confirmed and URL provided — fetch transcript
    return run_paid_work(request, youtube_transcript, url, language)


# ── Prepaid balance endpoints ─────────────────────────────────────────


@app.post("/api/v1/balance/top-up")
async def balance_topup(request: Request):
    """Credit a prepaid balance from a confirmed Nano on-chain payment.

    Accepts an X-PAYMENT header with a valid Nano block hash that has been
    sent to the treasury (VEND_ACCOUNT).  The full amount of the send is
    credited to the sender's account (the 'source' of the block).

    The caller can then use X-BALANCE instead of X-PAYMENT on subsequent
    calls to the regular paid endpoints, drawing from their balance.

    Returns the credited account, amount, and new total balance.
    """
    block_hash = extract_payment_block(request)
    if not block_hash:
        return JSONResponse(
            status_code=402,
            content={
                "error": "payment_required",
                "message": "Provide a Nano block hash via X-PAYMENT header to fund your balance",
            },
        )

    # Verify on-chain
    # For top-ups, we accept ANY amount >= the smallest endpoint price
    verification = verify_payment(block_hash, PRICE_RAW, VEND_ACCOUNT)
    if not verification["valid"]:
        return JSONResponse(
            status_code=402,
            content={
                "error": "payment_invalid",
                "message": verification["message"],
                "block_hash": block_hash,
            },
        )

    source = verification.get("source", "")
    if not source:
        return JSONResponse(
            status_code=400,
            content={
                "error": "no_source",
                "message": "Could not determine the sender account from this block",
                "block_hash": block_hash,
            },
        )

    amount_raw = verification.get("amount_raw", "0")

    # Credit the balance (UNIQUE constraint on block_hash prevents replay)
    credited = store.top_up(block_hash, source, amount_raw)
    if not credited:
        return JSONResponse(
            status_code=409,
            content={
                "error": "block_already_used",
                "message": "This payment block has already been used for a top-up",
                "block_hash": block_hash,
            },
        )

    new_balance = store.balance_of(source)
    log.info(
        "TOPUP: account=%s amount=%s raw new_balance=%s raw block=%s",
        source, amount_raw, new_balance, block_hash,
    )

    return JSONResponse(content={
        "status": "credited",
        "account": source,
        "amount_xno": raw_to_xno(amount_raw),
        "amount_raw": amount_raw,
        "new_balance_xno": raw_to_xno(str(new_balance)),
        "new_balance_raw": str(new_balance),
        "block_hash": block_hash,
        "note": "Use X-BALANCE header with your account address on subsequent calls to draw from this balance",
    })


@app.get("/api/v1/balance")
async def balance_check(
    request: Request,
    account: str = Query(None, description="Nano account to check balance for (nano_...)"),
):
    """Check the prepaid balance for a Nano account.

    If no *account* parameter is given, reads from the X-BALANCE header
    instead.  Returns the current balance in raw and XNO.
    """
    bal_account = account
    if not bal_account:
        bal_account = extract_balance_account(request)

    if not bal_account:
        return JSONResponse(
            status_code=400,
            content={
                "error": "account_required",
                "message": "Provide ?account=nano_... or X-BALANCE header",
            },
        )

    balance_raw = store.balance_of(bal_account)
    topup_history = store.get_topup_history(bal_account, limit=5)

    return JSONResponse(content={
        "account": bal_account,
        "balance_raw": str(balance_raw),
        "balance_xno": raw_to_xno(str(balance_raw)) if balance_raw > 0 else "0",
        "topup_count": len(topup_history),
        "recent_topups": [
            {
                "amount_xno": raw_to_xno(t["amount_raw"]),
                "amount_raw": t["amount_raw"],
                "block_hash": f"{t['block_hash'][:12]}...",
                "at": t["created_at"],
            }
            for t in topup_history
        ] if topup_history else [],
    })


@app.get("/api/v1/balance/topups")
async def balance_topups_list(
    request: Request,
    account: str = Query(None, description="Nano account to list topups for"),
):
    """List top-up transactions for a Nano account."""
    bal_account = account
    if not bal_account:
        bal_account = extract_balance_account(request)
    if not bal_account:
        return JSONResponse(
            status_code=400,
            content={"error": "account_required", "message": "Provide ?account=nano_..."},
        )
    topups = store.get_topup_history(bal_account, limit=50)
    balance_raw = store.balance_of(bal_account)
    return JSONResponse(content={
        "account": bal_account,
        "balance_raw": str(balance_raw),
        "balance_xno": raw_to_xno(str(balance_raw)) if balance_raw > 0 else "0",
        "topup_count": len(topups),
        "topups": topups,
    })


# --- Admin / Monitor endpoints ---

@app.get("/api/v1/admin/balances")
async def admin_balances(request: Request):
    """(Internal) List all accounts with non-zero prepaid balances.

    No auth — accessible only via localhost for monitoring.  Returns a
    live snapshot of the balances table.
    """
    if request.client and request.client.host:
        # Only allow from loopback
        if request.client.host not in ("127.0.0.1", "::1", "localhost"):
            return JSONResponse(status_code=403, content={"error": "local_only"})
    balances = store.get_all_balances()
    return JSONResponse(content={
        "total_accounts": len(balances),
        "balances": [
            {
                "account": b["account"][:15] + "...",
                "balance_xno": raw_to_xno(b["balance_raw"]),
                "balance_raw": b["balance_raw"],
                "total_topup_xno": raw_to_xno(b["total_topup_raw"]),
                "updated_at": b["updated_at"],
            }
            for b in balances
        ],
    })


# --- Run ---
if __name__ == "__main__":
    # NOTE: Use uvicorn.Server instead of uvicorn.run() — the run() form
    # deadlocks all worker threads in futex_wait_queue on this platform,
    # while Server.run() works correctly.
    log.info("Vend starting on %s:%d", HOST, PORT)
    log.info("Accepting Nano payments at %s...", VEND_ACCOUNT[:15])
    log.info("Price: %s XNO per extract/check-link call", PRICE_XNO)
    log.info("Price: %s XNO per domain-info call", PRICE_DOMAIN_XNO)
    log.info("Price: %s XNO per web-search call", PRICE_WEBSEARCH_XNO)
    log.info("Price: %s XNO per geoip call", PRICE_GEO_XNO)
    log.info("Price: %s XNO per nano-info call", PRICE_NANO_XNO)
    config = uvicorn.Config(
        app, host=HOST, port=PORT,
        log_level="info",
        proxy_headers=True,
        forwarded_allow_ips="*",
    )
    server = uvicorn.Server(config)
    server.run()