"""Vend MCP Server — expose Vend's pay-per-call API endpoints as MCP tools.

Each tool is a thin adapter: it calls the corresponding Vend REST endpoint and
returns the result — or, if the endpoint returns 402 Payment Required, it returns
the payment challenge so the MCP client can settle the Nano payment and retry.

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

# Use httpx2 (MCP 2.x's bundled HTTP client) to avoid event-loop conflicts
import httpx2 as httpx

# --- Config ---
TRANSPORT = os.environ.get("VEND_MCP_TRANSPORT", "stdio")
HTTP_HOST = os.environ.get("VEND_MCP_HOST", "0.0.0.0")
HTTP_PORT = int(os.environ.get("VEND_MCP_PORT", "8403"))

# Override transport from CLI args
if "--transport" in sys.argv:
    idx = sys.argv.index("--transport")
    if idx + 1 < len(sys.argv):
        TRANSPORT = sys.argv[idx + 1]

# Endpoint configuration
ENDPOINTS = {
    "extract_url": {
        "url": "https://extract.paypercall.dev/api/v1/extract",
        "description": "Extract clean text and markdown from a web page URL. Charges 0.0001 XNO in Nano via x402 protocol.",
    },
    "check_link": {
        "url": "https://check.paypercall.dev/api/v1/check-link",
        "description": "Check HTTP status, response time and redirect chain for any URL. Charges 0.0001 XNO in Nano via x402.",
    },
    "domain_info": {
        "url": "https://domain.paypercall.dev/api/v1/domain-info",
        "description": "Full domain intelligence: DNS records, WHOIS registration, SSL/TLS certificate, HTTP headers. Charges 0.0005 XNO in Nano via x402.",
    },
    "web_search": {
        "url": "https://search.paypercall.dev/api/v1/web-search",
        "description": "Web search via DuckDuckGo. Returns structured results with titles, URLs, and snippets. Charges 0.0001 XNO in Nano via x402.",
    },
    "geoip_lookup": {
        "url": "https://geoip.paypercall.dev/api/v1/geoip",
        "description": "IP geolocation lookup: country, city, coordinates, ISP, ASN, timezone. Use 'myip' for the caller's own IP. Charges 0.0001 XNO in Nano via x402.",
    },
    "check_url_status": {
        "url": "https://extract.paypercall.dev/api/v1/status",
        "description": "One-call URL status check: final HTTP status, redirect chain, TLS validity and days-to-expiry, response time, and whether the body changed since a previous call (pass previous_hash). Charges 0.0001 XNO in Nano via x402.",
    },
    "nano_account_info": {
        "url": "https://extract.paypercall.dev/api/v1/nano-info",
        "description": "Nano account intelligence: balance, representative, block count, frontier, weight, pending transactions. Charges 0.0005 XNO in Nano via x402.",
    },
    "youtube_transcript": {
        "url": "https://extract.paypercall.dev/api/v1/youtube-transcript",
        "description": "Extract captions and transcript from a YouTube video URL. Returns timestamped segments and model-sized chunks with deep-linked citations. Charges 0.0005 XNO in Nano via x402.",
    },
}

CLIENT_TIMEOUT = 60.0


async def call_vend_endpoint(endpoint_url: str, params: dict) -> dict:
    """Call a Vend REST endpoint and return the response."""
    async with httpx.AsyncClient(timeout=CLIENT_TIMEOUT) as client:
        try:
            resp = await client.get(endpoint_url, params=params, follow_redirects=False)
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

            payment_header = resp.headers.get("payment-required") or resp.headers.get("PAYMENT-REQUIRED") or ""
            return {
                "status": "payment_required",
                "error": "payment_required",
                "message": "Nano (XNO) payment required. Send the stated amount to the specified account, then retry this tool call with the block hash in X-PAYMENT header.",
                "payment_challenge": body,
                "payment_header_b64": payment_header,
                "endpoint": endpoint_url,
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

    server = MCPServer(
        name="vend",
        title="Vend API Merchant",
        description="Pay-per-call API tools settled in Nano (XNO). Extract web content, search the web, check links, check URL status (TLS expiry and content drift), domain intelligence, IP geolocation, Nano account info, and YouTube transcript extraction. No signup, no API keys — pay per call in Nano.",
        version="0.1.0",
    )

    # Register each endpoint as a tool via the decorator

    @server.tool(description=ENDPOINTS["extract_url"]["description"])
    async def extract_url(url: str) -> str:
        """Extract clean text from a URL. Returns title, text and markdown."""
        result = await call_vend_endpoint(ENDPOINTS["extract_url"]["url"], {"url": url})
        return json.dumps(result)

    @server.tool(description=ENDPOINTS["check_link"]["description"])
    async def check_link(url: str) -> str:
        """Check HTTP status of a URL. Returns status code, response time, redirect chain."""
        result = await call_vend_endpoint(ENDPOINTS["check_link"]["url"], {"url": url})
        return json.dumps(result)

    @server.tool(description=ENDPOINTS["domain_info"]["description"])
    async def domain_info(domain: str) -> str:
        """Look up domain intelligence. Returns DNS records, WHOIS, SSL/TLS, headers."""
        result = await call_vend_endpoint(ENDPOINTS["domain_info"]["url"], {"domain": domain})
        return json.dumps(result)

    @server.tool(description=ENDPOINTS["web_search"]["description"])
    async def web_search(q: str) -> str:
        """Search the web via DuckDuckGo. Returns titles, URLs, snippets."""
        result = await call_vend_endpoint(ENDPOINTS["web_search"]["url"], {"q": q})
        return json.dumps(result)

    @server.tool(description=ENDPOINTS["geoip_lookup"]["description"])
    async def geoip_lookup(ip: str) -> str:
        """Look up IP geolocation. Returns country, city, ISP, ASN, coordinates."""
        result = await call_vend_endpoint(ENDPOINTS["geoip_lookup"]["url"], {"ip": ip})
        return json.dumps(result)

    @server.tool(description=ENDPOINTS["check_url_status"]["description"])
    async def check_url_status(url: str, previous_hash: str = "") -> str:
        """Check a URL's status. Returns HTTP status, redirects, TLS expiry, content drift."""
        params = {"url": url}
        if previous_hash:
            params["previous_hash"] = previous_hash
        result = await call_vend_endpoint(ENDPOINTS["check_url_status"]["url"], params)
        return json.dumps(result)

    @server.tool(description=ENDPOINTS["nano_account_info"]["description"])
    async def nano_account_info(account: str) -> str:
        """Look up Nano account info. Returns balance, representative, block count."""
        result = await call_vend_endpoint(ENDPOINTS["nano_account_info"]["url"], {"account": account})
        return json.dumps(result)

    @server.tool(description=ENDPOINTS["youtube_transcript"]["description"])
    async def youtube_transcript(url: str, language: str = "en") -> str:
        """Extract captions and transcript from a YouTube video URL. Returns timestamped segments and model-sized chunks."""
        result = await call_vend_endpoint(ENDPOINTS["youtube_transcript"]["url"], {"url": url, "language": language})
        return json.dumps(result)

    return server


def main():
    server = create_server()

    if TRANSPORT == "stdio":
        print(f"Vend MCP server starting (stdio) with {len(ENDPOINTS)} tools.", file=sys.stderr)
        server.run(transport="stdio")
    elif TRANSPORT == "streamable-http":
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
        print(f"Vend MCP server starting (Streamable HTTP) on http://{HTTP_HOST}:{HTTP_PORT}", file=sys.stderr)
        server.run(
            transport="streamable-http",
            host=HTTP_HOST,
            port=HTTP_PORT,
            transport_security=transport_security,
        )
    else:
        print(f"Unknown transport: {TRANSPORT}. Use 'stdio' or 'streamable-http'.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()