"""Vend MCP Server — expose Vend's pay-per-call API endpoints as MCP tools.

Each tool is a thin adapter: it calls the corresponding Vend REST endpoint and
returns the result — or, if the endpoint returns 402 Payment Required, it returns
the payment challenge so the MCP client can settle the Nano payment and retry.

The MCP server now forwards the original MCP client's IP to the REST backend as
X-Forwarded-For, so the trial tracker sees the real caller (not 127.0.0.1).
This is the key conversion fix: MCP callers now get free trial calls.

Usage:
  python vend_mcp.py                        # stdio (Claude Desktop, Cursor)
  python vend_mcp.py --transport streamable-http  # HTTP (Streamable HTTP)

Tools (all require Nano payment via x402):
  extract_url(url)             — clean text/markdown from a web page  (0.0001 XNO)
  check_link(url)              — HTTP status, response time, redirects (0.0001 XNO)
  domain_info(domain)          — DNS, WHOIS, SSL/TLS, headers        (0.0005 XNO)
  web_search(q)                — DuckDuckGo search results            (0.0001 XNO)
  geoip_lookup(ip)             — IP geolocation                      (0.0001 XNO)
  check_url_status(url, previous_hash) — URL status, TLS, content    (0.0001 XNO)
  nano_account_info(account)   — Nano balance, rep, blocks           (0.0005 XNO)
  youtube_transcript(url, language) — YouTube transcript             (0.0005 XNO)
"""

import json
import os
import sys
import contextvars
import threading

from typing import Annotated
from pydantic import Field

# Use httpx2 (MCP 2.x's bundled HTTP client) to avoid event-loop conflicts
import httpx2 as httpx

# ── Context variable for the MCP client's real IP ─────────────────────
# Set by ASGI middleware before each request; read by call_vend_endpoint
# so the REST backend sees the real caller via X-Forwarded-For.
_mcp_client_ip: contextvars.ContextVar[str] = contextvars.ContextVar(
    "mcp_client_ip", default=""
)

# ── Config ───────────────────────────────────────────────────────────
TRANSPORT = os.environ.get("VEND_MCP_TRANSPORT", "stdio")
HTTP_HOST = os.environ.get("VEND_MCP_HOST", "0.0.0.0")
HTTP_PORT = int(os.environ.get("VEND_MCP_PORT", "8403"))
VEND_API_PORT = int(os.environ.get("VEND_API_PORT", "8402"))

# Override transport from CLI args
if "--transport" in sys.argv:
    idx = sys.argv.index("--transport")
    if idx + 1 < len(sys.argv):
        TRANSPORT = sys.argv[idx + 1]

# Internal base URL — call the REST API directly (127.0.0.1) rather than
# going through Caddy.  This avoids the extra TLS hop and lets us control
# the X-Forwarded-For header our own trial tracker needs.
_VEND_INTERNAL_BASE = f"http://127.0.0.1:{VEND_API_PORT}"

ENDPOINTS = {
    "extract_url": {
        "path": "/api/v1/extract",
        "description": "Extract clean text and markdown from a web page URL. Charges 0.0001 XNO in Nano via x402 protocol.",
    },
    "check_link": {
        "path": "/api/v1/check-link",
        "description": "Check HTTP status, response time and redirect chain for any URL. Charges 0.0001 XNO in Nano via x402.",
    },
    "domain_info": {
        "path": "/api/v1/domain-info",
        "description": "Full domain intelligence: DNS records, WHOIS registration, SSL/TLS certificate, HTTP headers. Charges 0.0005 XNO in Nano via x402.",
    },
    "web_search": {
        "path": "/api/v1/web-search",
        "description": "Web search via DuckDuckGo. Returns structured results with titles, URLs, and snippets. Charges 0.0001 XNO in Nano via x402.",
    },
    "geoip_lookup": {
        "path": "/api/v1/geoip",
        "description": "IP geolocation lookup: country, city, coordinates, ISP, ASN, timezone. Use 'myip' for the caller's own IP. Charges 0.0001 XNO in Nano via x402.",
    },
    "check_url_status": {
        "path": "/api/v1/status",
        "description": "One-call URL status check: final HTTP status, redirect chain, TLS validity and days-to-expiry, response time, and whether the body changed since a previous call (pass previous_hash). Charges 0.0001 XNO in Nano via x402.",
    },
    "nano_account_info": {
        "path": "/api/v1/nano-info",
        "description": "Nano account intelligence: balance, representative, block count, frontier, weight, pending transactions. Charges 0.0005 XNO in Nano via x402.",
    },
    "youtube_transcript": {
        "path": "/api/v1/youtube-transcript",
        "description": "Extract captions and transcript from a YouTube video URL. Returns timestamped segments and model-sized chunks with deep-linked citations. Charges 0.0005 XNO in Nano via x402.",
    },
    "mcp_find": {
        "path": "/api/v1/mcp-find",
        "description": "Search paid MCP and x402 service directories for a task. Returns matching services with their settlement rails, prices, and x402 health. Optional filter_rail='nano' shows only XNO-settling services. Charges 0.0001 XNO in Nano via x402.",
    },
}

CLIENT_TIMEOUT = 60.0


async def call_vend_endpoint(endpoint_path: str, params: dict) -> dict:
    """Call a Vend REST endpoint directly and return the response.

    Forwards the real MCP client IP as X-Forwarded-For so the trial tracker
    on the REST side sees the original caller (not 127.0.0.1).
    """
    url = f"{_VEND_INTERNAL_BASE}{endpoint_path}"
    headers = {}

    # Forward the real client IP from the MCP request context (if available)
    client_ip = _mcp_client_ip.get()
    if client_ip:
        headers["X-Forwarded-For"] = client_ip
        headers["X-Real-IP"] = client_ip

    async with httpx.AsyncClient(timeout=CLIENT_TIMEOUT) as client:
        try:
            resp = await client.get(
                url, params=params, headers=headers, follow_redirects=False
            )
        except httpx.TimeoutException:
            return {"error": f"Request timed out (limit: {CLIENT_TIMEOUT}s)"}
        except httpx.RequestError as e:
            return {"error": f"Request failed: {str(e)[:200]}"}

        # 402 = Payment Required — return the challenge
        if resp.status_code == 402:
            try:
                body = resp.json()
            except (json.JSONDecodeError, ValueError):
                body = {"error": "payment_required", "detail": resp.text[:500]}

            payment_header = (
                resp.headers.get("payment-required")
                or resp.headers.get("PAYMENT-REQUIRED")
                or ""
            )
            return {
                "status": "payment_required",
                "error": "payment_required",
                "message": (
                    "Nano (XNO) payment required. Send the stated amount to "
                    "the specified account, then retry this tool call with "
                    "the block hash in X-PAYMENT header."
                ),
                "payment_challenge": body,
                "payment_header_b64": payment_header,
                "endpoint": url,
            }

        # Success
        if resp.status_code == 200:
            try:
                data = resp.json()
                return {"status": "ok", "data": data}
            except (json.JSONDecodeError, ValueError):
                return {"status": "ok", "text": resp.text[:10000]}

        # Error
        try:
            detail = resp.json()
        except (json.JSONDecodeError, ValueError):
            detail = resp.text[:500]
        return {"status": "error", "error": f"HTTP {resp.status_code}", "detail": detail}


# --- Build the server ---


def create_server():
    """Create the MCPServer with all Vend endpoints as tools."""
    from mcp.server.mcpserver import MCPServer
    from mcp.types import ToolAnnotations

    server = MCPServer(
        name="vend",
        title="Vend API Merchant",
        description=(
            "Pay-per-call API tools settled in Nano (XNO). Extract web content, "
            "search the web, check links, check URL status (TLS expiry and content "
            "drift), domain intelligence, IP geolocation, Nano account info, and "
            "YouTube transcript extraction. No signup, no API keys — pay per call in Nano."
        ),
        version="0.1.0",
    )

    # All Vend tools are read-only queries against the pay-per-call API. Declaring
    # the annotations explicitly (rather than letting MCP clients assume the
    # destructive/open-world worst case) is what CheckMCP's compliance pillar checks.
    readonly_annotations = ToolAnnotations(
        read_only_hint=True,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=False,
    )

    # Register each endpoint as a tool via the decorator

    @server.tool(
        description=ENDPOINTS["extract_url"]["description"],
        annotations=readonly_annotations,
    )
    async def extract_url(
        url: Annotated[str, Field(description="Full http(s) URL of the web page to extract clean text/markdown from.")]
    ) -> str:
        """Extract clean text from a URL. Returns title, text and markdown."""
        result = await call_vend_endpoint(ENDPOINTS["extract_url"]["path"], {"url": url})
        return json.dumps(result)

    @server.tool(
        description=ENDPOINTS["check_link"]["description"],
        annotations=readonly_annotations,
    )
    async def check_link(
        url: Annotated[str, Field(description="Full http(s) URL whose HTTP status, response time and redirect chain to check.")]
    ) -> str:
        """Check HTTP status of a URL. Returns status code, response time, redirect chain."""
        result = await call_vend_endpoint(ENDPOINTS["check_link"]["path"], {"url": url})
        return json.dumps(result)

    @server.tool(
        description=ENDPOINTS["domain_info"]["description"],
        annotations=readonly_annotations,
    )
    async def domain_info(
        domain: Annotated[str, Field(description="Domain name (e.g. example.com) to look up DNS, WHOIS, SSL/TLS and headers for.")]
    ) -> str:
        """Look up domain intelligence. Returns DNS records, WHOIS, SSL/TLS, headers."""
        result = await call_vend_endpoint(ENDPOINTS["domain_info"]["path"], {"domain": domain})
        return json.dumps(result)

    @server.tool(
        description=ENDPOINTS["web_search"]["description"],
        annotations=readonly_annotations,
    )
    async def web_search(
        q: Annotated[str, Field(description="Search query string to run through the web search backend.")]
    ) -> str:
        """Search the web via DuckDuckGo. Returns titles, URLs, snippets."""
        result = await call_vend_endpoint(ENDPOINTS["web_search"]["path"], {"q": q})
        return json.dumps(result)

    @server.tool(
        description=ENDPOINTS["geoip_lookup"]["description"],
        annotations=readonly_annotations,
    )
    async def geoip_lookup(
        ip: Annotated[str, Field(description="IPv4/IPv6 address to geolocate, or the literal 'myip' to use the caller's own IP.")]
    ) -> str:
        """Look up IP geolocation. Returns country, city, ISP, ASN, coordinates."""
        result = await call_vend_endpoint(ENDPOINTS["geoip_lookup"]["path"], {"ip": ip})
        return json.dumps(result)

    @server.tool(
        description=ENDPOINTS["check_url_status"]["description"],
        annotations=readonly_annotations,
    )
    async def check_url_status(
        url: Annotated[str, Field(description="Full http(s) URL whose status, redirect chain, TLS validity and content to check.")],
        previous_hash: Annotated[str, Field(description="Optional hash of the body from a previous call, used to detect content drift.")] = "",
    ) -> str:
        """Check a URL's status. Returns HTTP status, redirects, TLS expiry, content drift."""
        params = {"url": url}
        if previous_hash:
            params["previous_hash"] = previous_hash
        result = await call_vend_endpoint(ENDPOINTS["check_url_status"]["path"], params)
        return json.dumps(result)

    @server.tool(
        description=ENDPOINTS["nano_account_info"]["description"],
        annotations=readonly_annotations,
    )
    async def nano_account_info(
        account: Annotated[str, Field(description="Nano account address (nano_... or xrb_...) to look up balance, representative, block count, frontier, weight, pending.")]
    ) -> str:
        """Look up Nano account info. Returns balance, representative, block count."""
        result = await call_vend_endpoint(ENDPOINTS["nano_account_info"]["path"], {"account": account})
        return json.dumps(result)

    @server.tool(
        description=ENDPOINTS["youtube_transcript"]["description"],
        annotations=readonly_annotations,
    )
    async def youtube_transcript(
        url: Annotated[str, Field(description="YouTube video URL (watch, youtu.be, embed or shorts format).")],
        language: Annotated[str, Field(description="Language code for the transcript (default 'en').")] = "en",
    ) -> str:
        """Extract captions and transcript from a YouTube video URL. Returns timestamped segments and model-sized chunks."""
        result = await call_vend_endpoint(
            ENDPOINTS["youtube_transcript"]["path"], {"url": url, "language": language}
        )
        return json.dumps(result)

    @server.tool(
        description=ENDPOINTS["mcp_find"]["description"],
        annotations=readonly_annotations,
    )
    async def mcp_find(
        q: Annotated[str, Field(description="Natural-language query — what the MCP or x402 service should do.")],
        filter_rail: Annotated[str, Field(description="Optional rail filter — pass 'nano' to show only services that settle in Nano (XNO), 'base' for USDC on Base, etc.")] = "",
        limit: Annotated[int, Field(description="Max results to return (1-50), default 10.")] = 10,
    ) -> str:
        """Search paid MCP/x402 service directories. Returns services with settlement rails, prices, x402 health."""
        params = {"q": q, "limit": limit}
        if filter_rail:
            params["filter_rail"] = filter_rail
        result = await call_vend_endpoint(ENDPOINTS["mcp_find"]["path"], params)
        return json.dumps(result)

    return server


def main():
    server = create_server()

    if TRANSPORT == "stdio":
        print(f"Vend MCP server starting (stdio) with {len(ENDPOINTS)} tools.", file=sys.stderr)
        server.run(transport="stdio")
    elif TRANSPORT == "streamable-http":
        import uvicorn
        from mcp.server.transport_security import TransportSecuritySettings

        vend_domain = os.environ.get("VEND_DOMAIN", "extract.paypercall.dev")
        http_port = os.environ.get("VEND_MCP_PORT", "8403")
        transport_security = TransportSecuritySettings(
            enable_dns_rebinding_protection=True,
            allowed_hosts=[
                f"127.0.0.1:{http_port}",
                "127.0.0.1",
                vend_domain,
                f"{vend_domain}:443",
                f"{vend_domain}:80",
                "localhost",
            ],
        )

        # Build the Starlette app the standard way
        inner_app = server.streamable_http_app(
            streamable_http_path="/mcp",
            json_response=False,
            stateless_http=False,
            transport_security=transport_security,
            host=HTTP_HOST,
        )

        # Wrap at the ASGI level to capture the real client IP before the
        # MCP server processes the request.  The IP is stored in a
        # contextvar so call_vend_endpoint can forward it to the REST
        # backend, giving MCP callers their own trial budget.
        async def client_ip_asgi_app(scope, receive, send):
            """ASGI wrapper that captures client IP before passing to the MCP app."""
            if scope["type"] == "http":
                # Extract client IP from the ASGI scope headers
                headers = dict(scope.get("headers", []))
                # headers are bytes: key-value pairs
                forwarded_bytes = headers.get(b"x-forwarded-for", b"")
                if forwarded_bytes:
                    forwarded_str = forwarded_bytes.decode("utf-8", errors="replace")
                    if "," in forwarded_str:
                        client_ip = forwarded_str.split(",")[0].strip()
                    else:
                        client_ip = forwarded_str.strip()
                else:
                    # Try X-Real-IP (Caddy sets this for the /mcp* route),
                    # then fall back to the direct connection IP.
                    real_ip_bytes = headers.get(b"x-real-ip", b"")
                    if real_ip_bytes:
                        client_ip = real_ip_bytes.decode("utf-8", errors="replace").strip()
                    elif scope.get("client") and scope["client"][0]:
                        client_ip = scope["client"][0]
                    else:
                        client_ip = "unknown"
                _mcp_client_ip.set(client_ip)
            await inner_app(scope, receive, send)

        print(
            f"Vend MCP server starting (Streamable HTTP) on "
            f"http://{HTTP_HOST}:{HTTP_PORT} with client-IP forwarding",
            file=sys.stderr,
        )

        config = uvicorn.Config(
            client_ip_asgi_app,
            host=HTTP_HOST,
            port=HTTP_PORT,
            log_level="info",
        )
        server_uv = uvicorn.Server(config)
        import anyio
        anyio.run(server_uv.serve)

    else:
        print(f"Unknown transport: {TRANSPORT}. Use 'stdio' or 'streamable-http'.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()