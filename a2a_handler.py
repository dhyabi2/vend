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

A2A_SKILL_MAP = {
    "extract": {
        "path": "/api/v1/extract",
        "price_xno": None,  # server.py's per-path price
    },
    "check_link": {
        "path": "/api/v1/check-link",
        "price_xno": None,
    },
    "domain_info": {
        "path": "/api/v1/domain-info",
        "price_xno": None,
    },
    "web_search": {
        "path": "/api/v1/web-search",
        "price_xno": None,
    },
    "geoip_lookup": {
        "path": "/api/v1/geoip",
        "price_xno": None,
    },
    "nano_account_info": {
        "path": "/api/v1/nano-info",
        "price_xno": None,
    },
}


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
                {"id": "extract", "name": "Extract URL content",
                 "description": "Return the readable text and markdown for a web page.",
                 "examples": ["Extract the main text of https://example.com"]},
                {"id": "web_search", "name": "Web search",
                 "description": "Search the web and return results.",
                 "examples": ["Search for Nano x402 payment facilitators"]},
                {"id": "geoip_lookup", "name": "IP geolocation",
                 "description": "Return location data for an IP address.",
                 "examples": ["Where is 8.8.8.8 located?"]},
                {"id": "domain_info", "name": "Domain intelligence",
                 "description": "Return DNS, WHOIS, TLS info for a domain.",
                 "examples": ["DNS summary for example.com"]},
                {"id": "check_link", "name": "Check link status",
                 "description": "Return HTTP status and redirect chain for a URL.",
                 "examples": ["Is https://example.com up?"]},
                {"id": "nano_account_info", "name": "Nano account info",
                 "description": "Return balance and info for a Nano account.",
                 "examples": ["Balance of nano_1yo6c1t..."]},
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

    # Route to skill
    if skill_id not in A2A_SKILL_MAP:
        return _jsonrpc_error(-32602, f"Unknown skill '{skill_id}'", id_)

    endpoint_path = A2A_SKILL_MAP[skill_id]["path"]

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

    # Paid → parse input and run the computation
    result_obj = None
    if skill_id == "extract":
        if not text:
            return _jsonrpc_error(-32602, "extract needs a url in message text", id_)
        result_obj = run_paid_work(request, __import__("server").extract_url, text)
    elif skill_id == "web_search":
        if not text:
            return _jsonrpc_error(-32602, "web_search needs a query in message text", id_)
        result_obj = run_paid_work(request, __import__("server").web_search, text)
    elif skill_id == "geoip_lookup":
        result_obj = run_paid_work(request, __import__("server").geoip_lookup, text)
    elif skill_id == "check_link":
        if not text:
            return _jsonrpc_error(-32602, "check_link needs a url in message text", id_)
        result_obj = run_paid_work(request, __import__("server").check_link, text)
    elif skill_id == "domain_info":
        if not text:
            return _jsonrpc_error(-32602, "domain_info needs a domain in message text", id_)
        result_obj = run_paid_work(request, __import__("server").domain_info, text)
    else:
        return _jsonrpc_error(-32602, f"Skill '{skill_id}' not implemented in this narrow adapter", id_)

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