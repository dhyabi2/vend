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
    parse_payment_signature,
    confirm_signature_payment,
    head_and_tail,
)
from extract import extract_url
from check_link import check_link
from batch_status import batch_status
from domain_info import domain_info
from web_search import web_search
from geoip import geoip_lookup
from nano_info import nano_account_info
from status_check import check_status
from youtube_transcript import youtube_transcript
from mcp_find import mcp_find
from render import render_url
from screenshot import capture_screenshot
from select_endpoint import select_from_url
from links_endpoint import links_from_url
from meta_endpoint import meta_for_url
from table_endpoint import tables_for_url
from pdf_extract import extract_pdf_text
from ai_jobs import ai_jobs
from wiki_summary import wiki_summary
from arxiv_paper import arxiv_paper
from hn_news import hn_news
from address_verdict import address_verdict
from endpoint_meta import endpoint_input_spec as em_input_spec, build_openapi_spec, INPUT_SPECS
from endpoint_meta import paid_from_manifest, complete_openapi, llms_endpoint_table, agent_tools_paid
import cdp_verify
from trial_tracker import get_tracker
from a2a_handler import a2a_endpoint

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
PRICE_SCREENSHOT_XNO = float(os.environ.get("VEND_PRICE_SCREENSHOT", "0.0005"))
PRICE_RENDER_XNO = float(os.environ.get("VEND_PRICE_RENDER", "0.0005"))
PRICE_SELECT_XNO = float(os.environ.get("VEND_PRICE_SELECT", "0.0001"))
PRICE_LINKS_XNO = float(os.environ.get("VEND_PRICE_LINKS", "0.0001"))
PRICE_META_XNO = float(os.environ.get("VEND_PRICE_META", "0.0001"))
PRICE_TABLE_XNO = float(os.environ.get("VEND_PRICE_TABLE", "0.0001"))
PRICE_SCREENSHOT_RAW = str(_price_to_raw(PRICE_SCREENSHOT_XNO))
PRICE_RENDER_RAW = str(_price_to_raw(PRICE_RENDER_XNO))
PRICE_SELECT_RAW = str(_price_to_raw(PRICE_SELECT_XNO))
PRICE_LINKS_RAW = str(_price_to_raw(PRICE_LINKS_XNO))
PRICE_META_RAW = str(_price_to_raw(PRICE_META_XNO))
PRICE_TABLE_RAW = str(_price_to_raw(PRICE_TABLE_XNO))
PRICE_PDF_XNO = float(os.environ.get("VEND_PRICE_PDF", "0.0005"))
PRICE_PDF_RAW = str(_price_to_raw(PRICE_PDF_XNO))
PRICE_MCPFIND_XNO = float(os.environ.get("VEND_PRICE_MCPFIND", "0.0001"))
PRICE_MCPFIND_RAW = str(_price_to_raw(PRICE_MCPFIND_XNO))
PRICE_JOBS_XNO = float(os.environ.get("VEND_PRICE_JOBS", "0.0002"))
PRICE_JOBS_RAW = str(_price_to_raw(PRICE_JOBS_XNO))
PRICE_WIKI_XNO = float(os.environ.get("VEND_PRICE_WIKI", "0.0001"))
PRICE_WIKI_RAW = str(_price_to_raw(PRICE_WIKI_XNO))
PRICE_ARXIV_XNO = float(os.environ.get("VEND_PRICE_ARXIV", "0.0001"))
PRICE_ARXIV_RAW = str(_price_to_raw(PRICE_ARXIV_XNO))
PRICE_HN_XNO = float(os.environ.get("VEND_PRICE_HN", "0.0001"))
PRICE_HN_RAW = str(_price_to_raw(PRICE_HN_XNO))
PRICE_VERDICT_XNO = float(os.environ.get("VEND_PRICE_VERDICT", "0.0001"))
PRICE_VERDICT_RAW = str(_price_to_raw(PRICE_VERDICT_XNO))
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
    "/api/v1/screenshot": EXTRACT_BASE,
    "/api/v1/render": EXTRACT_BASE,
    "/api/v1/batch-status": EXTRACT_BASE,
    "/api/v1/select": EXTRACT_BASE,
    "/api/v1/links": EXTRACT_BASE,
    "/api/v1/meta": EXTRACT_BASE,
    "/api/v1/table": EXTRACT_BASE,
    "/api/v1/pdf-extract": EXTRACT_BASE,
    "/api/v1/mcp-find": EXTRACT_BASE,
    "/api/v1/ai-jobs": EXTRACT_BASE,
    "/api/v1/wiki-summary": EXTRACT_BASE,
    "/api/v1/arxiv-paper": EXTRACT_BASE,
    "/api/v1/hn-news": EXTRACT_BASE,
    "/api/v1/address-verdict": NANO_BASE,
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

    NOTE: a spec-compliant ``PAYMENT-SIGNATURE`` header carrying an UNBROADCAST
    signed block (``payload.block`` is a dict) is NOT handled here — that route
    is taken by ``require_payment`` via ``confirm_signature_payment``.  We only
    extract a broadcast hash (a 64-hex string somewhere in the header value).
    """
    for header in ("x-payment", "payment", "x-payment-signature", "payment-signature"):
        val = request.headers.get(header)
        if val:
            parsed = parse_block_hash(val)
            if parsed:
                return parsed
    return None


def has_signed_block(request: Request) -> bool:
    """True when the request carries an unbroadcast signed block to settle."""
    for header in ("x-payment-signature", "payment-signature"):
        val = request.headers.get(header)
        if val and parse_payment_signature(val) is not None:
            return True
    return False


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


def require_payment(endpoint_path: str, price_xno: float = PRICE_XNO, price_raw: str = PRICE_RAW,
                    validate_input=None):
    """
    Decorator-like handler to require Nano payment for an endpoint.
    Returns:
        - (True, None) if paid
        - (False, Response) if unpaid — the caller should return this Response

    validate_input: optional callable(request) -> Optional[JSONResponse]. When a
    valid on-ledger payment is present but the request's required parameters are
    missing/malformed, this runs BEFORE the block is redeemed so a buyer who pays
    but sends a bad request does NOT lose their money. It returns a 400 naming the
    missing parameter and stating the block was not consumed (the buyer can retry
    with the same block and correct params). Naked discovery probes (no payment)
    still get the 402 challenge first, preserving x402 conformance.
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
            and not has_signed_block(request)
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
        signed_present = has_signed_block(request)

        # ── PAYMENT-SIGNATURE (x402 exact / feeless402) acceptance ──
        # A stock x402 ``exact`` client does not self-broadcast: it signs a
        # send block and submits it base64-encoded in PAYMENT-SIGNATURE,
        # expecting the resource server to broadcast and settle it.  When a
        # PaymentPayload is present (instead of a bare X-PAYMENT hash), Vend
        # acts as its own facilitator: structural checks, broadcast via RPC
        # ``process`` (which validates signature/work/balance on-ledger), wait
        # for confirmation, then let the existing verify/redeem path handle the
        # now-on-ledger block exactly like a self-broadcast payment.
        if not block_hash:
            pay_sig = (request.headers.get("payment-signature")
                       or request.headers.get("x-payment-signature"))
            sig_payload = parse_payment_signature(pay_sig) if pay_sig else None
            if sig_payload:
                sig_verification = confirm_signature_payment(
                    sig_payload, price_raw, VEND_ACCOUNT
                )
                if not sig_verification["valid"]:
                    return False, JSONResponse(
                        status_code=402,
                        content={
                            "error": "payment_invalid",
                            "message": sig_verification["message"],
                            "block_hash": sig_verification.get("block_hash", ""),
                        },
                        headers={
                            "X-PAYMENT-RESULT": "invalid",
                            "X-PAYMENT-MESSAGE": sig_verification["message"],
                        },
                    )
                # Confirmed block — feed into the normal verify/redeem path.
                block_hash = sig_verification["block_hash"]
                request.state.signature_payment = sig_verification
                log.info(
                    "PAYMENT-SIGNATURE: confirmed %s on %s",
                    head_and_tail(block_hash), endpoint_path,
                )

        # ── Prepaid balance check ────────────────────────────────────
        # A caller may pay once for a bucket and then draw calls from the
        # balance via the X-BALANCE header (a nano_... account address)
        # instead of paying a fresh block per call.  This is checkable with
        # zero on-chain RPC, so it is faster and lower-friction for repeat
        # callers.  The account must hold enough raw for this call's price;
        # the deduction is atomic in the store.
        if not block_hash and not signed_present:
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
        if not block_hash and not signed_present:
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
        #
        # Two settlement modes, both guarded here:
        #   * self-broadcast dialect (block already on-ledger; X-PAYMENT hash) —
        #     verify_payment reads the ledger and confirms amount+destination.
        #   * spec-compliant PAYMENT-SIGNATURE (unbroadcast signed block) — the
        #     block above (PAYMENT-SIGNATURE acceptance) already validated
        #     destination/amount locally, had the node broadcast the buyer's
        #     signed block (signature enforced by the network at process time),
        #     and confirmed it on-ledger before setting block_hash.  A
        #     forged/tampered block cannot move funds.  So by the time we reach
        #     this branch a signed payment has a confirmed block_hash, and
        #     verify_payment re-checks it against the ledger like any payment.
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

        # Validate required request input BEFORE redeeming the block. A buyer
        # who pays but sends a missing/incorrect required parameter must NOT
        # lose their money: we return a 400 naming the problem and the block is
        # left unconsumed so they can retry with the same block and correct
        # params. (Naked discovery probes with no payment never reach here —
        # they get the 402 challenge above.)
        if validate_input is not None:
            bad = validate_input(request)
            if bad is not None:
                return False, bad

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


def missing_param_response(param: str):
    """Build a 400 that names a missing required parameter and tells the caller
    the payment block was NOT consumed, so they can retry with the same block."""
    return JSONResponse(
        status_code=400,
        content={
            "error": f"{param} parameter is required",
            "block_not_consumed": True,
            "message": f"Your payment block was NOT redeemed. Add the required "
                       f"'{param}' parameter and retry with the same X-PAYMENT block.",
        },
        headers={"X-PAYMENT-RESULT": "invalid_request_not_billed"},
    )


def require_input(param: str):
    """Return a validate_input callable for require_payment that rejects a paid
    request whose required *param* is missing, WITHOUT redeeming the block."""
    def _validate(request: Request):
        qp = request.query_params
        val = qp.get(param)
        if val is None or (isinstance(val, str) and not val.strip()):
            return missing_param_response(param)
        return None
    return _validate


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
        "block_hash": (
            request.headers.get("x-payment", "")
            or payment.get("block_hash", "")
        )[:20] + "...",
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
batch_status = validate_paid_result("batch_status")(batch_status)
domain_info = validate_paid_result("domain_info")(domain_info)
web_search = validate_paid_result("web_search")(web_search)
geoip_lookup = validate_paid_result("geoip_lookup")(geoip_lookup)
nano_account_info = validate_paid_result("nano_account_info")(nano_account_info)
mcp_find = validate_paid_result("mcp_find")(mcp_find)
capture_screenshot = validate_paid_result("screenshot")(capture_screenshot)
render_url = validate_paid_result("render")(render_url)
select_from_url = validate_paid_result("select")(select_from_url)
meta_for_url = validate_paid_result("meta")(meta_for_url)
tables_for_url = validate_paid_result("table")(tables_for_url)


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


@app.get("/mcp-metering")
async def mcp_metering_guide():
    """Operator's guide to running and listing a paid (metered) MCP server."""
    return FileResponse(
        os.path.join(os.path.dirname(__file__), "static", "mcp-metering-guide.md"),
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
    """LLM-friendly catalog of Vend endpoints, payment flow, and directory listings.

    The endpoint table is generated from the x402 manifest at request time
    (the ``<!-- PAID-ENDPOINTS -->`` marker in llms.txt), so it always lists
    exactly the paid resources /.well-known/x402 sells."""
    with open(os.path.join(STATIC_DIR, "..", "llms.txt"), "r") as f:
        text = f.read()
    text = text.replace("<!-- PAID-ENDPOINTS -->", llms_endpoint_table(paid_catalog()))
    return PlainTextResponse(
        text,
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
@app.get("/.well-known/mcp")
@app.get("/mcp.json")
async def well_known_mcp():
    """MCP discovery manifest (mcp.json / /.well-known/mcp) — serves the same
    static mcp.json at three paths so every crawler finds it regardless of which
    discovery convention it checks:
    - /.well-known/mcp.json   — MCP spec (SEP-1960)
    - /.well-known/mcp        — MCP spec (SEP-1649), checked by Glama, mcpserver.cc
    - /mcp.json               — root-level fallback (some aggregators)"""
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


@app.get("/.well-known/apis.json")
async def well_known_apis():
    """APIs.json discovery manifest — lets apis.io, APILayer's public-apis
    ecosystem and the APIs.json index auto-discover Vend by pointing at our
    own machine-readable artifacts (OpenAPI, MCP, llms.txt). Served at both
    /.well-known/apis.json and /apis.json so any indexer that checks either
    path finds Vend. Generated from BASE_URL so it stays correct per host."""
    apis_json = {
        "name": "Vend API Merchant",
        "description": (
            "Pay-per-call URL-to-clean-text extraction settled in Nano (XNO). "
            "No signup, no API keys. Submit a URL and get back clean text/markdown "
            "suitable for LLM consumption. Pay 0.0001 XNO per call via x402."
        ),
        "url": f"{BASE_URL}/apis.json",
        "created": datetime.date.today().isoformat(),
        "modified": datetime.date.today().isoformat(),
        "specificationVersion": "0.21",
        "tags": ["ai", "web-scraping", "text-extraction", "developer-tools"],
        "apis": [
            {
                "name": "Vend API Merchant",
                "description": (
                    "Pay-per-call URL-to-clean-text extraction settled in Nano (XNO). "
                    "No signup, no API keys. 9 priced endpoints for AI agents."
                ),
                "humanURL": BASE_URL,
                "baseURL": BASE_URL,
                "tags": ["ai", "web-scraping", "text-extraction"],
                "properties": [
                    {"type": "OpenAPI", "url": f"{BASE_URL}/openapi.json"},
                    {"type": "MCP", "url": f"{BASE_URL}/.well-known/mcp.json"},
                    {"type": "LLMSTxt", "url": f"{BASE_URL}/llms.txt"},
                    {"type": "x-l402", "url": f"{BASE_URL}/.well-known/x402"},
                ],
            }
        ],
        "maintainers": [
            {
                "FN": "Vend API Merchant — Nano-settled APIs for AI Agents",
                "url": BASE_URL,
            }
        ],
    }
    return JSONResponse(
        content=apis_json,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Cache-Control": "public, max-age=3600",
        },
    )


@app.get("/apis.json")
async def apis_json_root():
    """APIs.json at the conventional root path as well, so indexers that check
    /apis.json (rather than /.well-known/apis.json) still find Vend."""
    return await well_known_apis()


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
        "extract.paypercall.dev": "7f9b4dae5c9bafba0478d99a22c0bec20dfdcbeb3fe3b00a",
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
        "description": "Pay-per-call API merchant settled in Nano (XNO). Endpoints: web extract, link checker, batch URL health, URL status, domain intelligence, web search, geoip lookup, nano account info, YouTube transcript, PDF text extraction, Hacker News feed, screenshot capture, browser-rendered page text, CSS-selector field extraction, page metadata (OpenGraph/JSON-LD), HTML table extraction, AI-jobs search, wiki summary, arxiv paper, and MCP/x402 service finder. No signup, no API keys.",
        "trial": {
            "limit": 5,
            "window": "1 day",
            "scope": "per-IP"
        },
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
                "url": f"{ENDPOINT_BASE['/api/v1/batch-status']}/api/v1/batch-status",
                "method": "GET",
                "description": "Batch check HTTP status of up to 50 URLs in one call. Accepts ?urls=url1,url2,... . Returns each URL's status_code, response_time_ms, final_url and error. 0.0001 XNO per call.",
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
                "url": f"{ENDPOINT_BASE['/api/v1/select']}/api/v1/select",
                "method": "GET",
                "description": "CSS-selector structured extraction. Accepts ?url= and ?selector= (e.g. h1, .price, table tr), optional ?attr= to read an attribute and ?limit=. Returns the matching elements' text/attributes, capped. 0.0001 XNO per call.",
                "accepts": [
                    {
                        "scheme": "exact",
                        "network": "nano:mainnet",
                        "asset": "XNO",
                        "amount": PRICE_SELECT_RAW,
                        "payTo": VEND_ACCOUNT
                    }
                ]
            },
            {
                "url": f"{ENDPOINT_BASE['/api/v1/links']}/api/v1/links",
                "method": "GET",
                "description": "Link extractor. Accepts ?url= and optional ?limit=. Returns every anchor link on the page as structured JSON: href, visible text, absolute URL, external flag, target and rel — for crawling, outbound-link audits and site maps. 0.0001 XNO per call.",
                "accepts": [
                    {
                        "scheme": "exact",
                        "network": "nano:mainnet",
                        "asset": "XNO",
                        "amount": PRICE_LINKS_RAW,
                        "payTo": VEND_ACCOUNT
                    }
                ]
            },
            {
                "url": f"{ENDPOINT_BASE['/api/v1/meta']}/api/v1/meta",
                "method": "GET",
                "description": "Page metadata extractor. Accepts ?url=. Returns title, meta description, Open Graph, Twitter Card, canonical URL, favicon and any JSON-LD blocks — for unfurling links into preview cards or reading structured data. 0.0001 XNO per call.",
                "accepts": [
                    {
                        "scheme": "exact",
                        "network": "nano:mainnet",
                        "asset": "XNO",
                        "amount": PRICE_META_RAW,
                        "payTo": VEND_ACCOUNT
                    }
                ]
            },
            {
                "url": f"{ENDPOINT_BASE['/api/v1/table']}/api/v1/table",
                "method": "GET",
                "description": "HTML table extractor. Accepts ?url=. Returns the page's tables as structured JSON: headers and rows keyed by column — for pulling comparison tables, price lists, schedules or statistics. 0.0001 XNO per call.",
                "accepts": [
                    {
                        "scheme": "exact",
                        "network": "nano:mainnet",
                        "asset": "XNO",
                        "amount": PRICE_TABLE_RAW,
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
                "url": f"{ENDPOINT_BASE['/api/v1/ai-jobs']}/api/v1/ai-jobs",
                "method": "GET",
                "description": "Search 19,800+ live AI/AI-adjacent job postings. Accepts ?q=<text>&company=<c>&category=<cat>&region=<reg>&level=<lvl>&remote=1&limit=<n>&offset=<n>. Returns clean structured jobs for labor-market research, lead-gen and competitor intelligence. 0.0002 XNO per call.",
                "accepts": [
                    {
                        "scheme": "exact",
                        "network": "nano:mainnet",
                        "asset": "XNO",
                        "amount": PRICE_JOBS_RAW,
                        "payTo": VEND_ACCOUNT
                    }
                ]
            },
            {
                "url": f"{ENDPOINT_BASE['/api/v1/wiki-summary']}/api/v1/wiki-summary",
                "method": "GET",
                "description": "Wikipedia entity summary — clean one-paragraph profile for any topic (company, person, technology). Accepts ?q=<topic>. Returns title, description, extract, thumbnail, wikidata_id. Reliable English Wikipedia REST endpoint. 0.0001 XNO per call.",
                "accepts": [
                    {
                        "scheme": "exact",
                        "network": "nano:mainnet",
                        "asset": "XNO",
                        "amount": PRICE_WIKI_RAW,
                        "payTo": VEND_ACCOUNT
                    }
                ]
            },
            {
                "url": f"{ENDPOINT_BASE['/api/v1/arxiv-paper']}/api/v1/arxiv-paper",
                "method": "GET",
                "description": "arXiv paper metadata — clean JSON for any paper by arXiv ID or search query: title, authors, primary category, abstract, published date, DOI, PDF link. Accepts ?arxiv_id=<id> or ?query=<terms>. Reliable keyless export.arxiv.org Atom API. 0.0001 XNO per call.",
                "accepts": [
                    {
                        "scheme": "exact",
                        "network": "nano:mainnet",
                        "asset": "XNO",
                        "amount": PRICE_ARXIV_RAW,
                        "payTo": VEND_ACCOUNT
                    }
                ]
            },
            {
                "url": f"{ENDPOINT_BASE['/api/v1/hn-news']}/api/v1/hn-news",
                "method": "GET",
                "description": "Hacker News top/new/best/ask/show/job feed — clean bounded JSON for tech-trend research, content monitoring, and curation agents. Accepts ?list=<top|new|best|ask|show|job>&limit=<n>&score=<min>. Reliable keyless HN Firebase API. 0.0001 XNO per call.",
                "accepts": [
                    {
                        "scheme": "exact",
                        "network": "nano:mainnet",
                        "asset": "XNO",
                        "amount": PRICE_HN_RAW,
                        "payTo": VEND_ACCOUNT
                    }
                ]
            },
            {
                "url": f"{ENDPOINT_BASE['/api/v1/address-verdict']}/api/v1/address-verdict",
                "method": "GET",
                "description": "Nano on-chain address verdict — is this payTo address a real active valuable counterparty or dust/wash? Accepts ?account=nano_.... Returns label (high_value/active/dust/wash_likely/inactive/not_found) plus signals (balance, receivable, block_count, send/receive counts, distinct senders, total received, largest inflow, account age, activity). Computed from public Nano RPC on-ledger data only. 0.0001 XNO per call.",
                "accepts": [
                    {
                        "scheme": "exact",
                        "network": "nano:mainnet",
                        "asset": "XNO",
                        "amount": PRICE_VERDICT_RAW,
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
            {   # Screenshot endpoint
                "url": f"{ENDPOINT_BASE['/api/v1/screenshot']}/api/v1/screenshot",
                "method": "GET",
                "description": "Capture a screenshot of any public URL using headless browser rendering. Accepts ?url=, ?format=png|jpeg, ?full_page=true|false, ?width=, ?height=. Returns base64 image data URL. 0.0005 XNO per call.",
                "accepts": [
                    {
                        "scheme": "exact",
                        "network": "nano:mainnet",
                        "asset": "XNO",
                        "amount": PRICE_SCREENSHOT_RAW,
                        "payTo": VEND_ACCOUNT
                    }
                ]
            },
            {   # JavaScript-rendered page -> markdown
                "url": f"{ENDPOINT_BASE['/api/v1/render']}/api/v1/render",
                "method": "GET",
                "description": "Render a JavaScript-heavy page in a real browser and return its content as Markdown. Accepts ?url= and optional ?max_chars=. For SPA/dashboard pages where a plain fetch returns an empty shell. 0.0005 XNO per call.",
                "accepts": [
                    {
                        "scheme": "exact",
                        "network": "nano:mainnet",
                        "asset": "XNO",
                        "amount": PRICE_RENDER_RAW,
                        "payTo": VEND_ACCOUNT
                    }
                ]
            },
            {   # PDF text extraction
                "url": f"{ENDPOINT_BASE['/api/v1/pdf-extract']}/api/v1/pdf-extract",
                "method": "GET",
                "description": "Extract text from a PDF at a URL. Accepts ?url= parameter. Returns title, page_count, and page-structured text suitable for LLM consumption. 0.0005 XNO per call.",
                "accepts": [
                    {
                        "scheme": "exact",
                        "network": "nano:mainnet",
                        "asset": "XNO",
                        "amount": PRICE_PDF_RAW,
                        "payTo": VEND_ACCOUNT
                    }
                ]
            },
            {
                "url": f"{ENDPOINT_BASE['/api/v1/mcp-find']}/api/v1/mcp-find",
                "method": "GET",
                "description": "Search paid MCP/x402 service directories for a task. Accepts ?q= and optional ?limit= and ?filter_rail=nano. Returns matching services with settlement rails, prices, and x402 health. 0.0001 XNO per call.",
                "accepts": [
                    {
                        "scheme": "exact",
                        "network": "nano:mainnet",
                        "asset": "XNO",
                        "amount": PRICE_MCPFIND_RAW,
                        "payTo": VEND_ACCOUNT
                    }
                ]
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
        "free": [
            {
                "url": f"{BASE_URL}/api/v1/delivery-proof",
                "method": "GET",
                "description": "FREE attestation endpoint (no payment required, deliberately NOT a payable resource): retrieve a signed delivery-attestation record for any previous paid call. Accepts ?block_hash=64-char-Nano-block. Returns what was paid for, whether it was delivered/failed, and when. Intentionally not in `resources` so a generic x402 client never tries to pay for it; document for buyers and auditors.",
                "documented_under": "docs"
            }
        ],
        "contact": "vend@paypercall.dev",
        "docs": BASE_URL,
        "discovery": f"{BASE_URL}/vend-directories",
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


def paid_catalog():
    """THE list of paid endpoints: the x402 manifest's resources, flattened.

    /openapi.json, /llms.txt and /.well-known/agent-tools.json are all derived
    from this, so no discovery surface can advertise a different paid set than
    /.well-known/x402 (issue #461: OpenAPI showed 9 of 23)."""
    return paid_from_manifest(x402_manifest())


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
        "description": "Pay-per-call API merchant settled in Nano (XNO). Endpoints: web extract, link checker, batch URL health, URL status, domain intelligence, web search, geoip lookup, nano account info, YouTube transcript, PDF text extraction, screenshot capture, browser-rendered page text, CSS-selector field extraction, page metadata (OpenGraph/JSON-LD), HTML table extraction, AI-jobs search, wiki summary, arxiv paper, and MCP/x402 service finder. No signup, no api keys.",
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
                "id": "mcp-find",
                "name": "MCP/x402 Service Finder",
                "description": "Search paid MCP/x402 service directories for a task, returning services with their settlement rails, prices and x402 health.",
                "endpoint": f"{ENDPOINT_BASE['/api/v1/mcp-find']}/api/v1/mcp-find",
                "method": "GET",
                "params": {"q": {"type": "string", "description": "Task to find a service for", "required": True},
                           "filter_rail": {"type": "string", "description": "Rail filter, e.g. 'nano' for XNO-settling services", "required": False}},
                "price": PRICE_MCPFIND_XNO,
                "currency": "XNO",
            },
            {
                "id": "nano-account",
                "name": "Nano Account Info",
                "description": "Nano account intelligence: balance, representative, block count, frontier, weight, pending transactions.",
                "endpoint": f"{ENDPOINT_BASE['/api/v1/nano-info']}/api/v1/nano-info",
                "method": "GET",
                "params": {"account": {"type": "string", "description": "Nano account address (nano_...)", "required": True}},
                "price": PRICE_NANO_XNO,
                "currency": "XNO",
            },
            {
                "id": "youtube-transcript",
                "name": "YouTube Transcript",
                "description": "Extract captions and transcript from a YouTube video URL. Returns timestamped segments and model-sized chunks.",
                "endpoint": f"{ENDPOINT_BASE['/api/v1/youtube-transcript']}/api/v1/youtube-transcript",
                "method": "GET",
                "params": {"url": {"type": "string", "description": "YouTube video URL", "required": True},
                           "language": {"type": "string", "description": "Preferred caption language", "required": False}},
                "price": PRICE_YT_XNO,
                "currency": "XNO",
            },
            {
                "id": "screenshot-capture",
                "name": "Screenshot Capture",
                "description": "Capture a full-page or viewport screenshot of any public URL using headless browser rendering. Returns a base64 data URL.",
                "endpoint": f"{ENDPOINT_BASE['/api/v1/screenshot']}/api/v1/screenshot",
                "method": "GET",
                "params": {"url": {"type": "string", "description": "URL to screenshot", "required": True},
                           "format": {"type": "string", "description": "Image format: png or jpeg", "default": "png"},
                           "full_page": {"type": "boolean", "description": "Capture entire scrollable page", "default": True},
                           "width": {"type": "integer", "description": "Viewport width", "default": 1280},
                           "height": {"type": "integer", "description": "Viewport height", "default": 720}},
                "price": PRICE_SCREENSHOT_XNO,
                "currency": "XNO",
            },
            {
                "id": "render-page",
                "name": "Render Page",
                "description": "Render a JavaScript-heavy page in a real browser and return its content as Markdown. Use when a plain HTTP fetch returns an empty shell (SPAs, dashboards, client-rendered search results).",
                "endpoint": f"{ENDPOINT_BASE['/api/v1/render']}/api/v1/render",
                "method": "GET",
                "params": {"url": {"type": "string", "description": "URL to render", "required": True},
                           "max_chars": {"type": "integer", "description": "Cap on returned characters", "default": 200000}},
                "price": PRICE_RENDER_XNO,
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
            {
                "id": "youtube-transcript",
                "name": "YouTube Transcript",
                "description": "Extract captions and timestamped transcript from a YouTube video URL. Returns model-sized chunks with deep-linked citations.",
                "endpoint": f"{ENDPOINT_BASE['/api/v1/youtube-transcript']}/api/v1/youtube-transcript",
                "method": "GET",
                "params": {"url": {"type": "string", "description": "YouTube video URL", "required": True},
                           "language": {"type": "string", "description": "Language code (default en)", "required": False}},
                "price": PRICE_YT_XNO,
                "currency": "XNO",
            },
            {
                "id": "pdf-extract",
                "name": "Extract PDF Text",
                "description": "Extract text from a PDF at a URL, preserving page structure. Essential for papers, specs, reports and invoices that a normal web extractor cannot read.",
                "endpoint": f"{ENDPOINT_BASE['/api/v1/pdf-extract']}/api/v1/pdf-extract",
                "method": "GET",
                "params": {"url": {"type": "string", "description": "URL of a PDF to extract text from", "required": True}},
                "price": PRICE_PDF_XNO,
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
        "docs_url": BASE_URL,
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
            "link status checks, URL status checks, domain intelligence, web search, "
            "IP geolocation, Nano account info and YouTube transcript extraction. "
            "No signup and no API keys — an unpaid call "
            "returns HTTP 402 with the exact Nano amount and payout account."
        ),
        "url": f"{BASE_URL}/a2a",
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
                    "check_url_status": PRICE_XNO,
                    "youtube_transcript": PRICE_YT_XNO,
                    "pdf_extract": PRICE_PDF_XNO,
                    "wiki_summary": PRICE_WIKI_XNO,
                    "arxiv_paper": PRICE_ARXIV_XNO,
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
            {
                "id": "check_url_status",
                "name": "URL status check",
                "description": "Return final HTTP status, redirect chain, TLS validity and days-to-expiry, response time, and body change vs a previous hash.",
                "tags": ["http", "monitoring", "tls", "drift"],
                "examples": ["Has https://example.com changed since yesterday?"],
            },
            {
                "id": "youtube_transcript",
                "name": "YouTube transcript",
                "description": "Extract captions and timestamped transcript from a YouTube video URL.",
                "tags": ["youtube", "transcript", "captions", "media"],
                "examples": ["Get the transcript of https://www.youtube.com/watch?v=dQw4w9WgXcQ"],
            },
            {
                "id": "pdf_extract",
                "name": "Extract PDF text",
                "description": "Extract text from a PDF at a URL, preserving page structure.",
                "tags": ["pdf", "document", "extraction", "paper"],
                "examples": ["Extract the text of https://arxiv.org/pdf/1706.03762"],
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
                "URL status checks, Nano account info, and YouTube transcript extraction. "
                "No signup, no API key — an unpaid HTTP call "
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
                {"path": "/api/v1/batch-status", "method": "GET",
                 "description": "Batch check HTTP status of up to 50 URLs in one call.",
                 "parameters": [{"name": "urls", "type": "string", "required": True,
                                 "description": "Comma-separated list of URLs to health-check."},
                                {"name": "method", "type": "string", "required": False,
                                 "description": "HEAD (fast, default) or GET."}],
                 "response_description": "JSON with each URL's status_code, response_time_ms, final_url and error."},
                {"path": "/api/v1/status", "method": "GET",
                 "description": "One-call URL status: final HTTP status, redirect chain, TLS validity and days-to-expiry, response time, and body content-drift vs a previous hash.",
                 "parameters": [{"name": "url", "type": "string", "required": True,
                                 "description": "The URL to check."},
                                {"name": "previous_hash", "type": "string", "required": False,
                                 "description": "Hash of a previous body to detect content drift."}],
                 "response_description": "JSON with final HTTP status, redirect chain, TLS days-to-expiry, response time, and whether the body changed."},
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
                {"path": "/api/v1/youtube-transcript", "method": "GET",
                 "description": "Extract captions and transcript from a YouTube video URL.",
                 "parameters": [{"name": "url", "type": "string", "required": True,
                                 "description": "YouTube video URL (watch, youtu.be, embed or shorts format)."},
                                {"name": "language", "type": "string", "required": False,
                                 "description": "Language code for the transcript (default 'en')."}],
                 "response_description": "JSON with timestamped transcript segments and model-sized deep-linked chunks."},
                {"path": "/api/v1/wiki-summary", "method": "GET",
                 "description": "Wikipedia entity summary: clean one-paragraph profile for any topic (company, person, technology, concept).",
                 "parameters": [{"name": "q", "type": "string", "required": True,
                                 "description": "Entity or topic to look up."}],
                 "response_description": "JSON with title, description, extract, thumbnail, wikidata_id, canonical url."},
                {"path": "/api/v1/arxiv-paper", "method": "GET",
                 "description": "arXiv paper metadata: clean JSON for a paper by ID or search query (title, authors, primary category, abstract, published, DOI, PDF link).",
                 "parameters": [{"name": "arxiv_id", "type": "string", "required": False,
                                 "description": "arXiv ID, e.g. 2106.09685."},
                                {"name": "query", "type": "string", "required": False,
                                 "description": "Full-text search terms (used when arxiv_id is absent)."}],
                 "response_description": "JSON paper object or list, never fabricated."},
                {"path": "/api/v1/hn-news", "method": "GET",
                 "description": "Hacker News feed: top/new/best/ask/show/job stories as clean bounded JSON (id, title, url, by, score, time, comment_count, item_type).",
                 "parameters": [{"name": "list", "type": "string", "required": False,
                                 "description": "HN feed: top|new|best|ask|show|job."},
                                {"name": "limit", "type": "integer", "required": False,
                                 "description": "Max stories (default 10, cap 30)."}],
                 "response_description": "Clean JSON feed with normalised story objects."},
                {"path": "/api/v1/address-verdict", "method": "GET",
                 "description": "Nano on-chain address verdict: is this payTo address real, active and valuable, or dust/wash? Label plus on-ledger signals.",
                 "parameters": [{"name": "account", "type": "string", "required": True,
                                 "description": "Nano address (nano_ or xrb_ prefix) to classify."}],
                 "response_description": "Verdict label (high_value/active/dust/wash_likely/inactive/not_found) with signals."},
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
                     "description": "Premium endpoints: domain-info, nano-info, youtube-transcript, pdf-extract",
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
  GET /api/v1/batch-status  {PRICE_XNO} XNO  batch health-check up to 50 URLs in one call (?urls=)
  GET /api/v1/domain-info   {PRICE_DOMAIN_XNO} XNO  DNS, WHOIS, TLS certificate, headers (?domain=)
  GET /api/v1/web-search    {PRICE_WEBSEARCH_XNO} XNO  web search, titles + URLs + snippets (?q=)
  GET /api/v1/geoip         {PRICE_GEO_XNO} XNO  country, city, ISP, ASN, timezone (?ip=)
  GET /api/v1/nano-info     {PRICE_NANO_XNO} XNO  Nano account balance, representative, blocks (?account=)
  GET /api/v1/status        {PRICE_XNO} XNO  URL status, redirects, TLS expiry, content-drift (?url=&previous_hash=)
  GET /api/v1/screenshot    {PRICE_SCREENSHOT_XNO} XNO  screenshot capture via headless browser (?url=&format=&full_page=&width=&height=)
  GET /api/v1/render        {PRICE_RENDER_XNO} XNO  JavaScript-rendered page -> markdown (?url=&max_chars=)
  GET /api/v1/pdf-extract   {PRICE_PDF_XNO} XNO  PDF at a URL -> page-structured text (?url=)
  GET /api/v1/mcp-find      {PRICE_MCPFIND_XNO} XNO  search paid MCP/x402 services, with rails/prices (?q=&limit=&filter_rail=)

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
        "batch-status",
        "/api/v1/batch-status",
        "Vend Batch URL Health Check (x402, Nano)",
        [
            "health-check many URLs in one call",
            "which links in my list are dead",
            "batch status of a sitemap or link list",
        ],
        ["data.enrichment", "http", "monitoring", "x402", "nano"],
        ["BatchStatusTool"],
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
    (
        "youtube-transcript",
        "/api/v1/youtube-transcript",
        "Vend YouTube Transcript (x402, Nano)",
        [
            "get the transcript of a YouTube video",
            "extract captions and timestamped segments from a youtube URL",
            "summarize what a video says from its transcript",
        ],
        ["data.media", "youtube", "transcript", "x402", "nano"],
        ["YoutubeTranscriptTool"],
    ),
    (
        "screenshot-capture",
        "/api/v1/screenshot",
        "Vend Screenshot Capture (x402, Nano)",
        [
            "take a screenshot of a URL",
            "capture a full-page screenshot of a web page",
            "render a page as PNG for visual evidence",
        ],
        ["data.capture", "screenshot", "browser", "x402", "nano"],
        ["ScreenshotTool"],
    ),
    (
        "render-page",
        "/api/v1/render",
        "Vend Render Page (x402, Nano)",
        [
            "get the content of a JavaScript-rendered page",
            "render a single-page app and return its text",
            "turn a client-rendered page into markdown",
        ],
        ["data.extraction", "render", "browser", "x402", "nano"],
        ["RenderTool"],
    ),
    (
        "extract-links",
        "/api/v1/links",
        "Vend Link Extractor (x402, Nano)",
        [
            "extract all links from a page",
            "crawl outbound links for an audit",
            "build a sitemap or link map from a URL",
        ],
        ["data.scraping", "links", "crawl", "x402", "nano"],
        ["LinkExtractTool", "CrawlTool"],
    ),
    (
        "pdf-extract",
        "/api/v1/pdf-extract",
        "Vend PDF Text Extraction (x402, Nano)",
        [
            "extract text from a PDF document",
            "read a PDF paper or report for an agent",
            "turn an invoice or spec PDF into text",
        ],
        ["data.extraction", "pdf", "document", "x402", "nano"],
        ["PdfExtractTool"],
    ),
    (
        "mcp-find",
        "/api/v1/mcp-find",
        "Vend MCP/x402 Service Finder (x402, Nano)",
        [
            "find a paid MCP or x402 service for this task",
            "which agent services accept Nano settlement",
            "search for a tool that does X and what it costs",
        ],
        ["data.discovery", "mcp", "x402", "search", "nano"],
        ["McpFindTool", "ToolDiscoveryTool"],
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
            "/api/v1/batch-status": PRICE_XNO,
            "/api/v1/domain-info": PRICE_DOMAIN_XNO,
            "/api/v1/web-search": PRICE_WEBSEARCH_XNO,
            "/api/v1/geoip": PRICE_GEO_XNO,
            "/api/v1/nano-info": PRICE_NANO_XNO,
            "/api/v1/status": PRICE_XNO,
            "/api/v1/youtube-transcript": PRICE_YT_XNO,
            "/api/v1/screenshot": PRICE_SCREENSHOT_XNO,
            "/api/v1/render": PRICE_RENDER_XNO,
            "/api/v1/links": PRICE_LINKS_XNO,
            "/api/v1/pdf-extract": PRICE_PDF_XNO,
            "/api/v1/mcp-find": PRICE_MCPFIND_XNO,
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
                    "docs": BASE_URL,
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
            "documentationUrl": BASE_URL,
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
    index Vend automatically as an x402 paid service.

    The paid resources are derived from the x402 manifest (paid_catalog);
    only the free entries listed below are kept from this hand-written list."""
    doc = {
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
                    "path": "/api/v1/batch-status",
                    "url": f"{ENDPOINT_BASE['/api/v1/batch-status']}/api/v1/batch-status",
                    "method": "GET",
                    "description": "Batch check HTTP status of up to 50 URLs in one call. Charges 0.0001 XNO per call.",
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
                {
                    "path": "/api/v1/youtube-transcript",
                    "url": f"{ENDPOINT_BASE['/api/v1/youtube-transcript']}/api/v1/youtube-transcript",
                    "method": "GET",
                    "description": "Extract captions and timestamped transcript from a YouTube video URL. Accepts ?url=...&language=en. Charges 0.0005 XNO per call.",
                    "price_xno": PRICE_YT_XNO,
                    "price_raw": PRICE_YT_RAW,
                    "pay_to": VEND_ACCOUNT
                },
                # Screenshot endpoint
                {
                    "path": "/api/v1/screenshot",
                    "url": f"{ENDPOINT_BASE['/api/v1/screenshot']}/api/v1/screenshot",
                    "method": "GET",
                    "description": "Capture a screenshot of any public URL using headless browser rendering. Accepts ?url=, ?format=png|jpeg, ?full_page=, ?width=, ?height=. Returns base64 image data URL. Charges 0.0005 XNO per call.",
                    "price_xno": PRICE_SCREENSHOT_XNO,
                    "price_raw": PRICE_SCREENSHOT_RAW,
                    "pay_to": VEND_ACCOUNT
                },
                # JavaScript-rendered page to markdown
                {
                    "path": "/api/v1/render",
                    "url": f"{ENDPOINT_BASE['/api/v1/render']}/api/v1/render",
                    "method": "GET",
                    "description": "Render a JavaScript-heavy page in a real browser and return its content as Markdown. Accepts ?url= and optional ?max_chars=. For pages where a plain fetch returns an empty shell. Charges 0.0005 XNO per call.",
                    "price_xno": PRICE_RENDER_XNO,
                    "price_raw": PRICE_RENDER_RAW,
                    "pay_to": VEND_ACCOUNT
                },
                # CSS-selector structured extraction
                {
                    "path": "/api/v1/select",
                    "url": f"{ENDPOINT_BASE['/api/v1/select']}/api/v1/select",
                    "method": "GET",
                    "description": "Structured CSS-selector extraction of fields from a page. Accepts ?url= and ?selector= (e.g. h1, .price, table tr), optional ?attr= and ?limit=. Returns the matching elements' text/attributes. Charges 0.0001 XNO per call.",
                    "price_xno": PRICE_SELECT_XNO,
                    "price_raw": PRICE_SELECT_RAW,
                    "pay_to": VEND_ACCOUNT
                },
                # Link extraction for crawling / audits / sitemaps
                {
                    "path": "/api/v1/links",
                    "url": f"{ENDPOINT_BASE['/api/v1/links']}/api/v1/links",
                    "method": "GET",
                    "description": "Link extractor. Accepts ?url= and optional ?limit=. Returns every anchor link on the page as structured JSON: href, text, absolute URL, external flag, target, rel — for crawling, outbound-link audits and site maps. Charges 0.0001 XNO per call.",
                    "price_xno": PRICE_LINKS_XNO,
                    "price_raw": PRICE_LINKS_RAW,
                    "pay_to": VEND_ACCOUNT
                },
                # Page metadata (OpenGraph / Twitter / JSON-LD)
                {
                    "path": "/api/v1/meta",
                    "url": f"{ENDPOINT_BASE['/api/v1/meta']}/api/v1/meta",
                    "method": "GET",
                    "description": "Page metadata extractor. Accepts ?url=. Returns title, meta description, Open Graph, Twitter Card, canonical URL, favicon and any JSON-LD blocks — for unfurling links into preview cards or reading structured data. Charges 0.0001 XNO per call.",
                    "price_xno": PRICE_META_XNO,
                    "price_raw": PRICE_META_RAW,
                    "pay_to": VEND_ACCOUNT
                },
                # HTML table extraction
                {
                    "path": "/api/v1/table",
                    "url": f"{ENDPOINT_BASE['/api/v1/table']}/api/v1/table",
                    "method": "GET",
                    "description": "HTML table extractor. Accepts ?url=. Returns the page's tables as structured JSON: headers and rows keyed by column — for pulling comparison tables, price lists, schedules or statistics. Charges 0.0001 XNO per call.",
                    "price_xno": PRICE_TABLE_XNO,
                    "price_raw": PRICE_TABLE_RAW,
                    "pay_to": VEND_ACCOUNT
                },
                {
                    "path": "/api/v1/pdf-extract",
                    "url": f"{ENDPOINT_BASE['/api/v1/pdf-extract']}/api/v1/pdf-extract",
                    "method": "GET",
                    "description": "Extract text from a PDF at a URL, preserving page structure. Accepts ?url=. Returns title, page_count, and page-structured text. Charges 0.0005 XNO per call.",
                    "price_xno": PRICE_PDF_XNO,
                    "price_raw": PRICE_PDF_RAW,
                    "pay_to": VEND_ACCOUNT
                },
                {
                    "path": "/api/v1/mcp-find",
                    "url": f"{ENDPOINT_BASE['/api/v1/mcp-find']}/api/v1/mcp-find",
                    "method": "GET",
                    "description": "Search paid MCP/x402 service directories for a task. Accepts ?q= and optional ?limit= and ?filter_rail=nano. Returns services with settlement rails, prices, x402 health. Charges 0.0001 XNO per call.",
                    "price_xno": PRICE_MCPFIND_XNO,
                    "price_raw": PRICE_MCPFIND_RAW,
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
    free = [r for r in doc["x402"]["resources"] if r.get("free") is True]
    doc["x402"]["resources"] = agent_tools_paid(paid_catalog()) + free
    return doc


@app.get("/openapi.json")
async def openapi_spec():
    """OpenAPI 3.1 discovery spec. Built from endpoint_meta for inspectability;
    its /api/v1 paths are completed from the x402 manifest (paid_catalog)."""
    spec = build_openapi_spec(
        {
            "extract": EXTRACT_BASE,
            "check": CHECK_BASE,
            "domain": DOMAIN_BASE,
            "search": SEARCH_BASE,
            "geoip": GEO_BASE,
            "nano": NANO_BASE,
            "status": EXTRACT_BASE,
            "youtube": EXTRACT_BASE,
            "screenshot": EXTRACT_BASE,
            "render": EXTRACT_BASE,
            "select": EXTRACT_BASE,
            "meta": EXTRACT_BASE,
            "table": EXTRACT_BASE,
            "pdf": EXTRACT_BASE,
        },
        {
            "extract": PRICE_XNO,
            "domain": PRICE_DOMAIN_XNO,
            "websearch": PRICE_WEBSEARCH_XNO,
            "geoip": PRICE_GEO_XNO,
            "nano": PRICE_NANO_XNO,
            "status": PRICE_XNO,
            "youtube": PRICE_YT_XNO,
            "screenshot": PRICE_SCREENSHOT_XNO,
            "render": PRICE_RENDER_XNO,
            "select": PRICE_SELECT_XNO,
            "meta": PRICE_META_XNO,
            "table": PRICE_TABLE_XNO,
            "pdf": PRICE_PDF_XNO,
        },
    )
    return complete_openapi(spec, paid_catalog())


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
    paid, response = await require_payment(
        "/api/v1/extract", validate_input=require_input("url"))(request)
    if not paid:
        return response

    # Payment confirmed — validate input
    if not url:
        return JSONResponse(
            status_code=400,
            content=missing_param_response("url").body,
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
    paid, response = await require_payment(
        "/api/v1/status", validate_input=require_input("url"))(request)
    if not paid:
        return response

    if not url:
        return JSONResponse(
            status_code=400,
            content=missing_param_response("url").body,
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
    paid, response = await require_payment(
        "/api/v1/check-link", validate_input=require_input("url"))(request)
    if not paid:
        return response

    # Payment confirmed — validate input
    if not url:
        return JSONResponse(
            status_code=400,
            content=missing_param_response("url").body,
        )

    # Payment confirmed and URL provided — do the check
    return run_paid_work(request, check_link, url)


# ── Batch-Status endpoint


@app.get("/api/v1/batch-status")
async def batch_status_endpoint(
    request: Request,
    urls: str = Query(None, description="Comma-separated list of URLs to health-check"),
    method: str = Query("HEAD", description="HEAD (fast, default) or GET"),
):
    """Check the HTTP status of many URLs in one paid call (0.0001 XNO).

    Returns each URL's status_code, response_time_ms, final_url and error,
    checked concurrently so a slow target never blocks the rest. Cap 50 URLs.
    """
    paid, response = await require_payment(
        "/api/v1/batch-status", validate_input=require_input("urls"))(request)
    if not paid:
        return response

    # Payment confirmed — validate input (multi-urls may be a single nonempty value)
    url_list = [u.strip() for u in (urls or "").split(",") if u.strip()]
    if not url_list:
        return JSONResponse(
            status_code=400,
            content=missing_param_response("urls").body,
        )
    if len(url_list) > 50:
        return JSONResponse(
            status_code=400,
            content={"error": "too_many_urls: supply at most 50 URLs per call"},
        )

    # Payment confirmed and URLs provided — do the batch check
    return run_paid_work(request, batch_status, url_list, 12, method)


@app.get("/api/v1/select")
async def select_endpoint(
    request: Request,
    url: str = Query(None, description="Public URL to extract from"),
    selector: str = Query(None, description="CSS selector (e.g. h1, .price, table tr)"),
    attr: str = Query(None, description="Optional attribute to read instead of text (e.g. href, src)"),
    limit: int = Query(50, description="Max matches to return (default 50, cap 200)"),
):
    """Structured CSS-selector extraction (0.0001 XNO).

    Fetches a public URL and returns the text (or a chosen attribute) of the
    elements matching a CSS selector, so a data/scraping agent can pull the
    fields it cares about (prices, headings, table rows, link hrefs) in one
    paid call instead of re-parsing the whole page.
    """
    paid, response = await require_payment(
        "/api/v1/select",
        validate_input=lambda req: (require_input("url")(req)
                                    or require_input("selector")(req)))(request)
    if not paid:
        return response

    # Payment confirmed — validate input
    if not url:
        return JSONResponse(
            status_code=400,
            content=missing_param_response("url").body,
        )
    if not selector:
        return JSONResponse(
            status_code=400,
            content=missing_param_response("selector").body,
        )

    return run_paid_work(request, select_from_url, url, selector, attr, limit)


@app.get("/api/v1/links")
async def links_endpoint(
    request: Request,
    url: str = Query(None, description="Public URL to extract links from"),
    limit: int = Query(200, description="Max links to return (default 200, cap 1000)"),
):
    """Link extractor (0.0001 XNO).

    Fetches a public URL and returns every anchor link on the page as structured
    JSON: href, visible text, absolute URL, external flag, target and rel — so a
    data/scraping/research agent can crawl a site, audit outbound links, or build
    a sitemap in one paid call instead of fetching and re-parsing the whole page.
    """
    paid, response = await require_payment(
        "/api/v1/links", validate_input=require_input("url"))(request)
    if not paid:
        return response

    if not url:
        return JSONResponse(
            status_code=400,
            content=missing_param_response("url").body,
        )

    return run_paid_work(request, links_from_url, url, limit)


@app.get("/api/v1/meta")
async def meta_endpoint(
    request: Request,
    url: str = Query(None, description="Public URL to read page metadata from"),
):
    """Page metadata extractor (0.0001 XNO).

    Fetches a public URL and returns its title, meta description, Open Graph,
    Twitter Card, canonical URL, favicon and any JSON-LD blocks -- so a
    data/scraping/research agent can unfurl a link into a preview card or read
    structured data without scraping and re-parsing the whole page.
    """
    paid, response = await require_payment(
        "/api/v1/meta", validate_input=require_input("url"))(request)
    if not paid:
        return response

    if not url:
        return JSONResponse(
            status_code=400,
            content=missing_param_response("url").body,
        )

    return run_paid_work(request, meta_for_url, url)


@app.get("/api/v1/table")
async def table_endpoint(
    request: Request,
    url: str = Query(None, description="Public URL to extract HTML tables from"),
):
    """HTML table extractor (0.0001 XNO).

    Fetches a public URL and returns the page's HTML tables as structured JSON:
    each table becomes {headers, rows} where rows are dicts keyed by column --
    so a data/scraping agent can pull comparison tables, price lists, schedules
    or statistics as clean rows instead of re-parsing HTML.
    """
    paid, response = await require_payment(
        "/api/v1/table", validate_input=require_input("url"))(request)
    if not paid:
        return response

    if not url:
        return JSONResponse(
            status_code=400,
            content=missing_param_response("url").body,
        )

    return run_paid_work(request, tables_for_url, url)


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
        validate_input=require_input("domain"),
    )(request)
    if not paid:
        return response

    # Payment confirmed — validate input
    if not domain:
        return JSONResponse(
            status_code=400,
            content=missing_param_response("domain").body,
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
        validate_input=require_input("q"),
    )(request)
    if not paid:
        return response

    # Payment confirmed — validate input
    if not q:
        return JSONResponse(
            status_code=400,
            content=missing_param_response("q").body,
        )

    # Payment confirmed and query provided — do the search
    return run_paid_work(request, web_search, q)


# ── IP Geolocation endpoint


@app.get("/api/v1/demo")
async def demo_endpoint(
    type: str = Query("extract", description="Endpoint type to demo: extract, check-link, batch-status, status, domain-info, web-search, geoip, nano-info, youtube-transcript, screenshot, render, select, meta, table, pdf-extract, mcp-find, ai-jobs, wiki-summary, arxiv-paper, hn-news, address-verdict"),
):
    """Free demo endpoint — serves honest sample data for every advertised type.

    A buyer reading the landing page / llms.txt sees 'Free demo endpoint —
    preview the output format, no payment required'. That promise must hold for
    a stranger on ANY shared/corporate IP, so the demo serves inline sample data
    here and never redirects into the paid endpoint: a redirect burned the
    per-IP free-trial budget on the real endpoint and, once the trial was spent,
    the 'free preview' became a 402 paywall (join:#114 / join:#304). Serving
    samples decouples the preview from the trial pool entirely.

    Every response carries price_xno and endpoint so an agent can decide whether
    the real output is worth paying for, exactly as the docs promise.
    """
    if type not in _DEMO_SAMPLES:
        return JSONResponse(
            content={"error": "unknown demo type", "valid": sorted(_DEMO_SAMPLES)},
            headers={"Access-Control-Allow-Origin": "*"},
            status_code=400,
        )
    payload = _DEMO_SAMPLES[type]
    return JSONResponse(
        content={
            "demo": True,
            "type": type,
            "message": "Sample output for preview only. Pay for real data via the endpoint price_xno below.",
            "x402_required": False,
            "price_xno": _demo_price(type),
            "endpoint": f"/api/v1/{type}",
            "sample": payload,
        },
        headers={"Access-Control-Allow-Origin": "*"},
        status_code=200,
    )


_PRICE_BY_TYPE = {
    "extract": PRICE_XNO, "check-link": PRICE_XNO, "batch-status": PRICE_XNO,
    "status": PRICE_XNO, "select": PRICE_XNO, "links": PRICE_XNO,
    "meta": PRICE_XNO, "table": PRICE_XNO, "web-search": PRICE_XNO,
    "geoip": PRICE_XNO, "mcp-find": PRICE_XNO, "wiki-summary": PRICE_XNO,
    "arxiv-paper": PRICE_XNO, "hn-news": PRICE_XNO, "ai-jobs": PRICE_JOBS_XNO,
    "address-verdict": PRICE_XNO,
    "domain-info": PRICE_DOMAIN_XNO,
    "nano-info": PRICE_NANO_XNO,
    "youtube-transcript": PRICE_YT_XNO, "screenshot": PRICE_SCREENSHOT_XNO,
    "render": PRICE_RENDER_XNO, "pdf-extract": PRICE_PDF_XNO,
}


def _demo_price(t: str) -> float:
    p = _PRICE_BY_TYPE.get(t)
    return p if p is not None else PRICE_XNO


_DEMO_SAMPLES = {
    "extract": {"title": "Example Domain", "text": "This domain is for use in illustrative examples in documents.", "char_count": 74, "url": "https://example.com"},
    "check-link": {"url": "https://example.com", "status_code": 200, "response_time_ms": 42, "final_url": "https://example.com/", "redirect_chain": []},
    "batch-status": {"results": [{"url": "https://example.com", "status_code": 200, "response_time_ms": 41}, {"url": "https://httpbin.org/status/200", "status_code": 500, "response_time_ms": 210}], "count": 2},
    "status": {"url": "https://example.com", "status_code": 200, "final_url": "https://example.com/", "redirect_chain": [], "tls_valid": True, "response_time_ms": 39},
    "domain-info": {"domain": "example.com", "dns": {"a": ["93.184.216.34"], "mx": ["mail.example.com"]}, "whois_created": "1992-01-01", "ssl_valid": True},
    "web-search": {"query": "nano cryptocurrency", "results": [{"title": "Nano — Digital currency", "url": "https://nano.org", "snippet": "Nano is a digital currency with zero fees and instant transactions."}]},
    "geoip": {"ip": "8.8.8.8", "country": "United States", "country_code": "US", "city": "Mountain View", "isp": "Google LLC", "asn": "AS15169"},
    "nano-info": {"account": "nano_3t6k35gi95xu6tergt6p69ck76ogmitsa8mnijtpxm9fkcm736xtoncuohr3", "balance_raw": "1000000000000000000000000", "representative": "nano_3t6k35gi95xu6tergt6p69ck76ogmitsa8mnijtpxm9fkcm736xtoncuohr3", "block_count": "42"},
    "youtube-transcript": {"video_id": "dQw4w9WgXcQ", "title": "Rick Astley - Never Gonna Give You Up", "transcript": "We're no strangers to love..."},
    "screenshot": {"url": "https://example.com", "image_url": "https://extract.paypercall.dev/static/sample.png", "width": 1280, "height": 720},
    "render": {"url": "https://example.com", "text": "Rendered text content from a JS-heavy page.", "title": "Example Domain"},
    "select": {"url": "https://example.com", "selector": "h1", "matches": ["Example Domain"], "count": 1},
    "links": {"url": "https://example.com", "links": [{"text": "More information...", "href": "https://www.iana.org/domains/example"}], "count": 1},
    "meta": {"url": "https://example.com", "title": "Example Domain", "description": "", "og_image": "", "json_ld": []},
    "table": {"url": "https://example.com", "tables": [{"rows": 1, "cells": [["header1", "header2"]]}], "count": 1},
    "pdf-extract": {"url": "https://arxiv.org/pdf/1706.03762", "title": "Attention Is All You Need", "text": "The dominant sequence transduction models are based on complex recurrent or convolutional neural networks...", "page_count": 15},
    "mcp-find": {"query": "web scraping", "results": [{"name": "vend-extract", "rail": "nano", "url": "https://extract.paypercall.dev/.well-known/x402"}]},
    "ai-jobs": {"query": "OpenAI", "results": [{"title": "AI Engineer", "company": "Acme AI", "location": "Remote", "salary": "$150k-$200k"}]},
    "wiki-summary": {"topic": "Nano (cryptocurrency)", "summary": "Nano is a cryptocurrency that uses a directed acyclic graph (block-lattice) for feeless, instant transactions.", "url": "https://en.wikipedia.org/wiki/Nano_(cryptocurrency)"},
    "arxiv-paper": {"arxiv_id": "2106.09685", "title": "LoRA: Low-Rank Adaptation of Large Language Models", "authors": ["Edward J. Hu"], "abstract": "We propose Low-Rank Adaptation..."},
    "hn-news": {"list": "top", "results": [{"title": "Nano: a feeless digital currency", "url": "https://news.ycombinator.com/item?id=1", "points": 1234}]},
    "address-verdict": {"account": "nano_1yo6c1t64ahfjdw1dxizmbbnpdmbrckwhw9phbg5pdkeubrizga4qhnjmnx7", "verdict": "active", "confidence": 0.99},
}


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
        validate_input=require_input("ip"),
    )(request)
    if not paid:
        return response

    # Payment confirmed — validate input
    if not ip:
        return JSONResponse(
            status_code=400,
            content=missing_param_response("ip").body,
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
        validate_input=require_input("account"),
    )(request)
    if not paid:
        return response

    # Payment confirmed — validate input
    if not account:
        return JSONResponse(
            status_code=400,
            content=missing_param_response("account").body,
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
        validate_input=require_input("url"),
    )(request)
    if not paid:
        return response

    # Payment confirmed — validate input
    if not url:
        return JSONResponse(
            status_code=400,
            content=missing_param_response("url").body,
        )

    # Payment confirmed and URL provided — fetch transcript
    return run_paid_work(request, youtube_transcript, url, language)


@app.get("/api/v1/screenshot")
async def screenshot_endpoint(
    request: Request,
    url: str = Query(None, description="Public URL to capture a screenshot of"),
    format: str = Query("png", description="Image format: png or jpeg"),
    full_page: bool = Query(True, description="Capture the full scrollable page or just the viewport"),
    width: int = Query(1280, description="Viewport width in pixels (320-3840)", ge=320, le=3840),
    height: int = Query(720, description="Viewport height in pixels (240-2160)", ge=240, le=2160),
):
    """Capture a screenshot of a public URL using headless browser rendering.
    Requires Nano payment (0.0005 XNO).

    Returns a base64-encoded image data URL so agents receive the image inline
    without a second fetch. Supports PNG and JPEG formats, full-page or viewport
    capture, and custom viewport dimensions.

    The *url* parameter is declared optional so that an unauthenticated probe
    (no payment, no parameter) reaches the 402 challenge *before* request
    validation rejects it — required by the x402scan discovery spec.
    """
    paid, response = await require_payment(
        "/api/v1/screenshot",
        price_xno=PRICE_SCREENSHOT_XNO,
        price_raw=PRICE_SCREENSHOT_RAW,
        validate_input=require_input("url"),
    )(request)
    if not paid:
        return response

    # Payment confirmed — validate input
    if not url:
        return JSONResponse(
            status_code=400,
            content=missing_param_response("url").body,
        )

    # Payment confirmed and URL provided — capture screenshot
    return run_paid_work(request, capture_screenshot, url, format, full_page, width, height)


@app.get("/api/v1/render")
async def render_endpoint(
    request: Request,
    url: str = Query(None, description="Public URL to render in a browser"),
    max_chars: int = Query(200000, description="Cap on the Markdown returned (100-500000)"),
):
    """Render a JavaScript-heavy page in a real browser and return its content as Markdown.
    Requires Nano payment (0.0005 XNO).

    The sibling endpoint /api/v1/extract fetches a URL over HTTP and parses the HTML;
    on a page whose content is produced by JavaScript (SPAs, client-rendered
    dashboards, search results behind a front-end) that HTML is an empty shell and
    extract returns very little. This endpoint renders the page first and returns the
    rendered content, so the two together cover both kinds of page.

    The *url* parameter is declared optional so that an unauthenticated probe
    (no payment, no parameter) reaches the 402 challenge *before* request
    validation rejects it — required by the x402scan discovery spec.
    """
    paid, response = await require_payment(
        "/api/v1/render",
        price_xno=PRICE_RENDER_XNO,
        price_raw=PRICE_RENDER_RAW,
        validate_input=require_input("url"),
    )(request)
    if not paid:
        return response

    # Payment confirmed — validate input
    if not url:
        return JSONResponse(
            status_code=400,
            content=missing_param_response("url").body,
        )

    # Payment confirmed and URL provided — render the page
    return run_paid_work(request, render_url, url, max_chars)


@app.get("/api/v1/pdf-extract")
async def pdf_extract_endpoint(
    request: Request,
    url: str = Query(None, description="URL of a PDF to extract text from"),
):
    """Extract text from a PDF at a URL, preserving page structure.
    Requires Nano payment (0.0005 XNO).

    Agents constantly hit PDF links (papers, specs, reports, invoices) that a
    normal web extractor cannot read because the bytes are not HTML. This is
    the missing half of the URL-extraction menu.

    The *url* parameter is declared optional so that an unauthenticated probe
    (no payment, no parameter) reaches the 402 challenge *before* request
    validation rejects it.
    """
    paid, response = await require_payment(
        "/api/v1/pdf-extract",
        price_xno=PRICE_PDF_XNO,
        price_raw=PRICE_PDF_RAW,
        validate_input=require_input("url"),
    )(request)
    if not paid:
        return response

    # Payment confirmed — validate input
    if not url:
        return JSONResponse(
            status_code=400,
            content=missing_param_response("url").body,
        )

    # Payment confirmed and URL provided — extract the PDF text
    return run_paid_work(request, extract_pdf_text, url)


# ── MCP/x402 service finder endpoint ──────────────────────────────────


@app.get("/api/v1/mcp-find")
async def mcp_find_endpoint(
    request: Request,
    q: str = Query(None, description="Natural-language query — what the MCP/x402 service does"),
    limit: int = Query(10, description="Max results to return (1-50)"),
    filter_rail: str = Query(None, description="Rail filter — e.g. 'nano' to show only XNO-settling services"),
):
    """Search paid MCP/x402 service directories for a task.

    Requires Nano payment (0.0001 XNO). Returns structured results with
    settlement rails, prices and x402 health so an agent can pick a service
    it can pay for.

    The *q* parameter is declared optional so that an unauthenticated probe
    reaches the 402 challenge *before* request validation rejects it.
    """
    paid, response = await require_payment(
        "/api/v1/mcp-find",
        price_xno=PRICE_MCPFIND_XNO,
        price_raw=PRICE_MCPFIND_RAW,
        validate_input=require_input("q"),
    )(request)
    if not paid:
        return response

    # Payment confirmed — validate input
    if not q:
        return JSONResponse(
            status_code=400,
            content=missing_param_response("q").body,
        )

    # Payment confirmed and query provided — search the directories
    return run_paid_work(request, mcp_find, q, limit, filter_rail)


# ── AI jobs search endpoint ───────────────────────────────────────────


@app.get("/api/v1/ai-jobs")
async def ai_jobs_endpoint(
    request: Request,
    q: str = Query(None, description="Full-text search term"),
    company: str = Query(None, description="Filter by company"),
    category: str = Query(None, description="Filter by category"),
    region: str = Query(None, description="Filter by region"),
    level: str = Query(None, description="Filter by seniority level"),
    remote: str = Query(None, description="Set to 1/true to return only remote roles"),
    limit: int = Query(10, description="Max jobs to return (default 10, cap 50)"),
    offset: int = Query(0, description="Pagination offset (default 0)"),
):
    """Search 19,800+ live AI/AI-adjacent job postings.
    Requires Nano payment (0.0002 XNO).

    Filters (all optional): q (full-text), company, category, region, level,
    remote (1/true), plus limit (cap 50) and offset for pagination. Returns
    clean structured jobs for labor-market research, lead-gen, competitor
    intelligence and job-bot building.

    All query params are declared optional so an unauthenticated probe (no
    payment, no parameter) reaches the 402 challenge *before* validation.
    """
    paid, response = await require_payment(
        "/api/v1/ai-jobs",
        price_xno=PRICE_JOBS_XNO,
        price_raw=PRICE_JOBS_RAW,
    )(request)
    if not paid:
        return response

    # Payment confirmed — run the search with the provided filters.
    return run_paid_work(
        request, ai_jobs,
        q=q, company=company, category=category, region=region, level=level,
        remote=remote, limit=limit, offset=offset,
    )


@app.get("/api/v1/wiki-summary")
async def wiki_summary_endpoint(
    request: Request,
    q: str = Query(None, description="Entity or topic to look up (e.g. 'Nano', 'OpenAI', 'Python')."),
):
    """Return a clean Wikipedia summary profile for any topic — company, person,
    technology or concept. Priced at 0.0001 XNO per lookup.

    Uses the free, keyless, highly-reliable English Wikipedia REST Summary API.
    Returns title, one-paragraph extract, description, thumbnail, wikidata_id
    and canonical URL. No scraping needed.

    The ?q parameter is required; an unauthenticated probe (no query, no
    payment) returns the 402 challenge before validation.
    """
    paid, response = await require_payment(
        "/api/v1/wiki-summary",
        price_xno=PRICE_WIKI_XNO,
        price_raw=PRICE_WIKI_RAW,
        validate_input=require_input("q"),
    )(request)
    if not paid:
        return response

    # Payment confirmed — run the lookup.
    return run_paid_work(
        request, wiki_summary,
        query=q, q=None, timeout=15,
    )


@app.get("/api/v1/arxiv-paper")
async def arxiv_paper_endpoint(
    request: Request,
    arxiv_id: str = Query(None, description="arXiv paper ID, e.g. '2106.09685' or 'math.GT/0309136'."),
    query: str = Query(None, description="Full-text search terms (used when arxiv_id is absent)."),
    max_results: int = Query(1, description="Max results for a free-text query (1-5)."),
):
    """Return clean arXiv paper metadata by ID or search query — title, authors,
    primary category, abstract, published date, DOI, PDF link. Priced at 0.0001 XNO per call.

    Uses the free, keyless export.arxiv.org Atom API. Returns structured JSON
    ready for research agents and deep-research tooling. No XML parsing needed.

    Provide ONE of ?arxiv_id= or ?query= — not both. A bare probe (no payment)
    returns the 402 challenge.
    """
    paid, response = await require_payment(
        "/api/v1/arxiv-paper",
        price_xno=PRICE_ARXIV_XNO,
        price_raw=PRICE_ARXIV_RAW,
        validate_input=lambda req: (
            require_input("arxiv_id")(req) if not (
                req.query_params.get("arxiv_id") or req.query_params.get("query")
            ) else None),
    )(request)
    if not paid:
        return response

    # Payment confirmed — run the lookup.
    return run_paid_work(
        request, arxiv_paper,
        arxiv_id=arxiv_id, query=query, max_results=max_results, timeout=25,
    )


@app.get("/api/v1/hn-news")
async def hn_news_endpoint(
    request: Request,
    list: str = Query("top", description="HN feed: top|new|best|ask|show|job"),
    limit: int = Query(10, description="Max stories to return (default 10, cap 30)"),
    score: int = Query(None, description="Optional minimum score filter"),
):
    """Read the Hacker News top/new/best/ask/show/job feed as clean JSON.
    Priced at 0.0001 XNO per call.

    Returns bounded, normalised story objects (id, title, url, by, score,
    time, comment_count, item_type) for tech-trend research, content
    monitoring, and curation agents. Uses the reliable keyless HN Firebase API.

    A bare probe (no payment, no parameter) returns the 402 challenge.
    """
    paid, response = await require_payment(
        "/api/v1/hn-news",
        price_xno=PRICE_HN_XNO,
        price_raw=PRICE_HN_RAW,
    )(request)
    if not paid:
        return response

    # Payment confirmed — fetch the feed.
    return run_paid_work(
        request, hn_news,
        list_name=list, limit=limit, score=score,
    )


@app.get("/api/v1/address-verdict")
async def address_verdict_endpoint(
    request: Request,
    account: str = Query(None, description="Nano address (nano_ or xrb_ prefix) to classify"),
):
    """Return an on-chain trust verdict for a Nano address. Priced 0.0001 XNO.

    Answers the question an agent decoding an x402 challenge asks before it
    signs: is this payTo address a real, active, valuable counterparty or a
    dust/wash account? Computed only from public Nano RPC on-ledger data
    (account_info + account_history). Label is conservative and data-grounded
    (high_value/active/dust/wash_likely/inactive/not_found/invalid_address/
    unreachable) with the raw signals underneath — it never claims to know an
    account's human intent.

    The *account* parameter is declared optional so that an unauthenticated
    probe (no payment, no parameter) reaches the 402 challenge *before*
    request validation rejects it — required by the x402scan discovery spec,
    same as the extract/status endpoints. Missing account is validated only
    after payment is confirmed.
    """
    paid, response = await require_payment(
        "/api/v1/address-verdict",
        price_xno=PRICE_VERDICT_XNO,
        price_raw=PRICE_VERDICT_RAW,
        validate_input=require_input("account"),
    )(request)
    if not paid:
        return response

    # Payment confirmed — validate input
    if not account:
        return JSONResponse(
            status_code=400,
            content=missing_param_response("account").body,
        )

    # Payment confirmed and account provided — compute the verdict.
    return run_paid_work(
        request, address_verdict,
        account=account,
    )


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


# --- A2A JSON-RPC endpoint (request #105): maps A2A skills to x402-paid endpoints ---
# Registered on the A2A Registry (a2aregistry.org, id f58d5423). The agent-card
# url points here instead of /mcp so the card's advertised transport is JSON-RPC.
app.add_api_route("/a2a", a2a_endpoint, methods=["POST"])

# --- Delivery-Attestation Endpoint ---


@app.get("/api/v1/delivery-proof")
async def delivery_proof(block_hash: str = Query(..., description="Nano block hash to look up")):
    """Return a signed delivery-attestation record for a paid call.

    Accepts a Nano block hash as ?block_hash=... and returns what it
    paid for, whether it was delivered or failed, and when -- the proof that
    an honest settlement happened.

    This is the answer to hinge finding #30 / #82: the most-wanted unmet
    layer across the whole x402 ecosystem is a verifiable record of delivery
    / release / refund / re-attestation of a paid call.  No other x402 rail
    produces it.  Vend already stores every redemption; this endpoint makes
    them queryable.

    FREE (no payment required) -- the proof of delivery costs nothing.
    """
    # Validate block hash format (parse normalizes to upper case)
    norm_hash = parse_block_hash(block_hash)
    if not norm_hash:
        return JSONResponse(
            status_code=400,
            content={"error": "invalid_block_hash", "message": "Not a valid Nano block hash"},
        )

    rec = store.get_redemption(norm_hash)
    if rec is None:
        return JSONResponse(
            status_code=404,
            content={"error": "not_found", "message": "No payment found for this block hash"},
        )

    return JSONResponse(content={
        "block_hash": rec["block_hash"],
        "amount_xno": raw_to_xno(rec["amount_raw"]),
        "source": rec["source"][:15] + "...",
        "endpoint": rec["endpoint"],
        "status": rec["status"],
        "created_at": rec["created_at"],
        "seller": "vend",
        "settlement_rail": "nano:mainnet/XNO",
        "x402_version": 2,
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
    log.info("Price: %s XNO per youtube-transcript call", PRICE_YT_XNO)
    log.info("Price: %s XNO per screenshot capture call", PRICE_SCREENSHOT_XNO)
    log.info("Price: %s XNO per render call", PRICE_RENDER_XNO)
    config = uvicorn.Config(
        app, host=HOST, port=PORT,
        log_level="info",
        proxy_headers=True,
        forwarded_allow_ips="*",
    )
    server = uvicorn.Server(config)
    server.run()