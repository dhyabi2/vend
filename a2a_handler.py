"""
a2a_handler — Narrow A2A JSON-RPC v0.3 adapter for Vend.

Maps A2A skills to the x402-paid compute functions already defined in
server.py, reusing require_payment and the paid endpoint logic.

Handled methods:
  - agent/authenticatedRequest/initialize  → A2A agent init
  - message/send                          → paid call (extract, web-search, etc.)
  - message/task/get                      → current task state
  - message/task/cancel                   → cancel a task

The A2A message/send tasks carry payment via X-PAYMENT or X-BALANCE
headers (same as the existing HTTP GET endpoints).
"""

import json
import logging
import time
import uuid
from typing import Optional

from fastapi import Request, Response
from fastapi.responses import JSONResponse

log = logging.getLogger("vend")


# ── In-memory task store ────────────────────────────────────────────────────
_tasks = {}  # task_id -> dict


def _jsonrpc_error(code: int, message: str, id_: str | None = None) -> dict:
    """Standard JSON-RPC 2.0 error block."""
    return {
        "jsonrpc": "2.0",
        "error": {"code": code, "message": message},
        "id": id_,
    }


def _jsonrpc_result(result, id_: str | None) -> dict:
    return {"jsonrpc": "2.0", "result": result, "id": id_}


# ── A2A task semantics ──────────────────────────────────────────────────────
#
# The A2A agent card (`/.well-known/agent-card.json`) advertises 9 skills with
# these exact IDs.  An A2A client (e.g. the a2aregistry.org task-conformance
# probe) reads the card, then calls message/send with the `skillId` it found.
# The handler must therefore accept every ID the card advertises, or the
# listing genuinely mis-sequences discovery (advertise X, reject X).
#
# Each entry maps a message/send `skillId` to the server's paid route, its
# price, and the server function to run once payment is confirmed.  Legacy
# aliases (`extract`, `check_url`, `url_status`) are kept for callers who used
# the earlier narrow adapter; the canonical IDs are the card's.

def _skill(skill_id, path, price_xno, fn, *, aliases=()):
    """One canonical skill entry.

    `skill_id` is the card's canonical A2A skill id (what a client sends as
    `skillId` in message/send); `aliases` are extra skillIds that route here
    for backwards compatibility with the earlier narrow adapter.
    """
    return {"id": skill_id, "path": path, "price_xno": price_xno,
            "fn": fn, "aliases": tuple(aliases)}


# The first arg is the canonical card skill id; path is the server's paid route.
# youtube_transcript takes (url, language="en"); every other paid function takes
# a single text argument.
A2A_SKILLS = [
    _skill("extract_url", "/api/v1/extract", None, "extract_url", aliases=("extract",)),
    _skill("check_link", "/api/v1/check-link", None, "check_link", aliases=("check_url",)),
    _skill("domain_info", "/api/v1/domain-info", None, "domain_info"),
    _skill("web_search", "/api/v1/web-search", None, "web_search"),
    _skill("geoip_lookup", "/api/v1/geoip", None, "geoip_lookup"),
    _skill("nano_account_info", "/api/v1/nano-info", None, "nano_account_info"),
    # URL-status check is the same monitoring route as check-link in this
    # narrow adapter; the card lists it separately, so accept it too.
    _skill("check_url_status", "/api/v1/check-link", None, "check_link", aliases=("url_status",)),
    _skill("youtube_transcript", "/api/v1/youtube-transcript", None, "youtube_transcript"),
    _skill("pdf_extract", "/api/v1/pdf-extract", None, "extract_pdf_text"),
]

# skillId -> canonical entry (card ids + legacy aliases + path-as-key for safety)
A2A_SKILL_LOOKUP = {}
for _e in A2A_SKILLS:
    A2A_SKILL_LOOKUP[_e["id"]] = _e
    A2A_SKILL_LOOKUP.setdefault(_e["path"], _e)
    for _a in _e["aliases"]:
        A2A_SKILL_LOOKUP.setdefault(_a, _e)


def _resolve_skill(skill_id: str):
    """Return the canonical skill entry for a skillId (card ID or legacy alias), or None."""
    return A2A_SKILL_LOOKUP.get(skill_id)


# ── JSON-RPC dispatcher ─────────────────────────────────────────────────


async def dispatch_a2a(body: dict, request: Request) -> dict:
    """Dispatch one JSON-RPC 2.0 request body."""
    method = body.get("method", "")
    params = body.get("params", {})
    id_ = body.get("id")

    if method == "agent/authenticatedRequest/initialize":
        return handle_initialize(params, id_)
    elif method == "message/send":
        return await handle_message_send(params, request, id_)
    elif method == "message/task/get":
        return handle_task_get(params, id_)
    elif method == "message/task/cancel":
        return handle_task_cancel(params, id_)
    else:
        return _jsonrpc_error(-32601, f"Method '{method}' not found", id_)


# ── Handlers ────────────────────────────────────────────────────────────


def handle_initialize(params: dict, id_: str | None) -> dict:
    """A2A Initialize: introduce this agent."""
    return _jsonrpc_result(
        {
            "agentName": "Vend API Merchant",
            "agentDescription": "Pay-per-call API merchant settled in Nano (XNO): "
                                "web page extraction, link status checks, domain intel, "
                                "web search, geolocation, Nano account info.",
            "provider": {
                "organization": "Vend",
                "url": "https://paypercall.dev",
            },
            "version": "0.1.0",
            "capabilities": {
                "streaming": False,
                "pushNotifications": False,
                "stateTransitionHistory": False,
            },
            "skills": [
                {"id": "extract_url", "name": "Extract URL content",
                 "description": "Return the readable title, text and markdown for a web page.",
                 "examples": ["Extract the main text of https://example.com"]},
                {"id": "check_link", "name": "Check link status",
                 "description": "Return HTTP status, redirect chain, TLS validity and response time for a URL.",
                 "examples": ["Is https://example.com up and where does it redirect?"]},
                {"id": "domain_info", "name": "Domain intelligence",
                 "description": "Return DNS, WHOIS, TLS info for a domain.",
                 "examples": ["DNS summary for example.com"]},
                {"id": "web_search", "name": "Web search",
                 "description": "Search the web and return result titles, URLs and snippets.",
                 "examples": ["Search for Nano x402 payment facilitators"]},
                {"id": "geoip_lookup", "name": "IP geolocation",
                 "description": "Return country, city, coordinates, ISP and ASN for an IP address.",
                 "examples": ["Where is 8.8.8.8 located?"]},
                {"id": "nano_account_info", "name": "Nano account info",
                 "description": "Return balance, representative, weight, frontier and pending for a Nano account.",
                 "examples": ["Balance of nano_1yo6c1t..."]},
                {"id": "check_url_status", "name": "URL status check",
                 "description": "Return final HTTP status, redirect chain, TLS validity and body change vs a previous hash.",
                 "examples": ["Has https://example.com changed since yesterday?"]},
                {"id": "youtube_transcript", "name": "YouTube transcript",
                 "description": "Extract captions and timestamped transcript from a YouTube video URL.",
                 "examples": ["Get the transcript of a YouTube video"]},
                {"id": "pdf_extract", "name": "Extract PDF text",
                 "description": "Extract text from a PDF at a URL, preserving page structure.",
                 "examples": ["Extract the text of a PDF at a URL"]},
            ],
        },
        id_,
    )


async def handle_message_send(params: dict, request: Request, id_: str | None) -> dict:
    """A2A message/send: run a paid skill.

    Expects:
        message: {parts: [{type: "text", text: "..."}]}
        task: {id: ...}

    The caller's payment (X-PAYMENT or X-BALANCE) must come from the
    JSON-RPC request's *headers* (same as the HTTP GET endpoint).  If
    unpaid, we return a Task with state='input-required' carrying the
    x402 price quote.
    """
    from server import require_payment, run_paid_work  # server.py module in same directory

    msg = params.get("message", {})
    task_param = params.get("task", {})
    task_id = task_param.get("id") or str(uuid.uuid4())
    skill_id = params.get("skillId", "extract")
    metadata = params.get("metadata", {})

    # Extract intent text from the A2A message
    parts = msg.get("parts", [])
    text_parts = [p.get("text", "") for p in parts if p.get("type") == "text"]
    text = " ".join(text_parts)

    # Build an internal request with the same payment headers as the incoming HTTP request
    # so require_payment can check X-PAYMENT / X-BALANCE.
    # FastAPI's Request wraps the ASGI scope; we pass the same headers.
    # The require_payment checker reads request.headers from the incoming HTTP request
    # that carries the A2A JSON-RPC.
    # But require_payment expects endpoint_path and builds a Response/check result.
    # For A2A, the call is a message/send, not a GET, but the payment detection
    # logic is header-driven and reusable:
    #   - X-PAYMENT header (block hash) or X-BALANCE header (account address)
    #   - plus verify_payment and store redemption

    # Route to skill (canonical card ID or legacy alias)
    entry = _resolve_skill(skill_id)
    if entry is None:
        return _jsonrpc_error(-32602, f"Unknown skill '{skill_id}'", id_)

    endpoint_path = entry["path"]
    fn_name = entry["fn"]

    # Use require_payment to check payment. It reads directly from request.headers.
    paid, response = await require_payment(endpoint_path)(request)
    if not paid:
        # Unpaid → return input-required with the x402 challenge
        body = json.loads(response.body) if hasattr(response, "body") else {}
        task = {
            "id": task_id,
            "status": "input-required",
            "skills": [skill_id],
            "requirePayment": {
                "network": "nano:mainnet",
                "asset": "XNO",
                "amount": body.get("price_xno", "0.0001"),
                "payTo": body.get("pay_to", ""),
                "accepts": body.get("accepts", []),
            },
            "metadata": metadata,
        }
        _tasks[task_id] = task
        return _jsonrpc_result({"task": task, "requiresPayment": True}, id_)

    # Paid → parse input and run the computation.  Every paid function takes the
    # URL/query/account/domain text from the message; youtube_transcript also
    # accepts an optional language.
    import server

    fn = getattr(server, fn_name, None)
    if fn is None:
        return _jsonrpc_error(-32602, f"Skill '{skill_id}' not implemented in this narrow adapter", id_)

    if not text:
        return _jsonrpc_error(-32602, f"{skill_id} needs its input (URL, query, domain, account or IP) in message text", id_)

    if fn_name == "youtube_transcript":
        lang = (params.get("metadata") or {}).get("language", "en")
        result_obj = run_paid_work(request, fn, text, lang)
    else:
        result_obj = run_paid_work(request, fn, text)


    # run_paid_work returns a JSONResponse; extract its body dict for the artifact
    if hasattr(result_obj, "body"):
        try:
            result = json.loads(result_obj.body)
        except (TypeError, ValueError):
            result = {"raw": result_obj.body.decode("utf-8", "replace")}
        status_code = getattr(result_obj, "status_code", 200)
    else:
        result = dict(result_obj)
        status_code = 200

    # Build the A2A Task result
    task = {
        "id": task_id,
        "status": "completed" if status_code < 400 else "failed",
        "skills": [skill_id],
        "artifacts": [
            {
                "parts": [
                    {"type": "text", "text": json.dumps(result, ensure_ascii=False)}
                ],
                "metadata": {"mimeType": "application/json"},
            }
        ],
        "metadata": metadata,
    }
    _tasks[task_id] = task
    return _jsonrpc_result({"task": task}, id_)


def handle_task_get(params: dict, id_: str | None) -> dict:
    task_id = (params.get("task") or {}).get("id") or params.get("id")
    task = _tasks.get(task_id)
    if not task:
        return _jsonrpc_error(-32602, f"Task '{task_id}' not found", id_)
    return _jsonrpc_result({"task": task}, id_)


def handle_task_cancel(params: dict, id_: str | None) -> dict:
    task_id = (params.get("task") or {}).get("id") or params.get("id")
    task = _tasks.get(task_id)
    if not task:
        return _jsonrpc_error(-32602, f"Task '{task_id}' not found", id_)
    task["status"] = "canceled"
    _tasks[task_id] = task
    return _jsonrpc_result({"task": task}, id_)


# ── A2A input / unknown handling ───────────────────────────────────────


async def a2a_endpoint(request: Request):
    """POST /a2a — A2A JSON-RPC v0.3 dispatcher.

    Accepts a single JSON-RPC request object or an array of them (batch).
    Returns the response(s) in the same shape.
    """
    try:
        body = await request.json()
    except Exception as ex:
        return JSONResponse(
            status_code=400,
            content=_jsonrpc_error(-32700, f"Parse error: {ex}"),
        )

    is_batch = isinstance(body, list)
    requests = body if is_batch else [body]
    responses = []
    for req in requests:
        if not isinstance(req, dict) or "method" not in req:
            responses.append(_jsonrpc_error(-32600, "Invalid request", None))
        else:
            responses.append(await dispatch_a2a(req, request))

    if not is_batch:
        return JSONResponse(content=responses[0])

    return JSONResponse(content=responses)