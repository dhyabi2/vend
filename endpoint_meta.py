"""
endpoint_meta.py — pure-data discovery metadata for Vend's paid endpoints.

Holds the endpoint input specs and the OpenAPI 3.1 discovery spec that the
server publishes. Extracted from server.py so discovery metadata is small,
inspectable and verifiable on its own (a server.py-scoped law exceeds the
ledger's evidence cap once server.py grows past ~60k numbered chars).

All functions here are pure: they take the base URLs and prices as arguments
and never read the environment or import server.py, so there is no import
cycle and no hidden state.
"""

# Per-endpoint input specs: what a buyer must send *before* paying, published
# in the 402 challenge as extensions.bazaar.info so an agent knows the request
# shape without guessing. Two independent conformance checkers warn when this
# is missing, because an agent that cannot know what to send fails closed
# instead of paying.
INPUT_SPECS = {
    "/api/v1/extract": {
        "type": "http",
        "method": "GET",
        "input": {
            "type": "query",
            "schema": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "format": "uri",
                            "description": "URL to extract clean text from"},
                },
                "required": ["url"],
            },
            "example": {"url": "https://example.com/article"},
        },
    },
    "/api/v1/check-link": {
        "type": "http",
        "method": "GET",
        "input": {
            "type": "query",
            "schema": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "format": "uri",
                            "description": "URL whose status and redirect chain to check"},
                },
                "required": ["url"],
            },
            "example": {"url": "https://example.com"},
        },
    },
    "/api/v1/domain-info": {
        "type": "http",
        "method": "GET",
        "input": {
            "type": "query",
            "schema": {
                "type": "object",
                "properties": {
                    "domain": {"type": "string",
                               "description": "Domain to look up (e.g. example.com)"},
                },
                "required": ["domain"],
            },
            "example": {"domain": "example.com"},
        },
    },
    "/api/v1/web-search": {
        "type": "http",
        "method": "GET",
        "input": {
            "type": "query",
            "schema": {
                "type": "object",
                "properties": {
                    "q": {"type": "string", "description": "Search query"},
                },
                "required": ["q"],
            },
            "example": {"q": "x402 nano payments"},
        },
    },
    "/api/v1/ai-jobs": {
        "type": "http",
        "method": "GET",
        "input": {
            "type": "query",
            "schema": {
                "type": "object",
                "properties": {
                    "q": {"type": "string",
                          "description": "Full-text search term (e.g. a company, role or keyword)"},
                    "company": {"type": "string", "description": "Filter by company name"},
                    "category": {"type": "string",
                                 "description": "Filter by category (Engineering, Research, Sales & GTM, ...)"},
                    "region": {"type": "string", "description": "Filter by region (US, Europe, Asia-Pacific, ...)"},
                    "level": {"type": "string", "description": "Filter by seniority level (Lead+, Mid, Senior, ...)"},
                    "remote": {"type": "string",
                               "description": "Set to 1/true to return only remote roles"},
                    "limit": {"type": "integer", "description": "Max jobs to return (default 10, cap 50)"},
                    "offset": {"type": "integer", "description": "Pagination offset (default 0)"},
                },
            },
            "example": {"q": "OpenAI", "remote": "1", "limit": 5},
        },
    },
    "/api/v1/geoip": {
        "type": "http",
        "method": "GET",
        "input": {
            "type": "query",
            "schema": {
                "type": "object",
                "properties": {
                    "ip": {"type": "string",
                           "description": "IP address to look up (or 'myip' for caller's IP)"},
                },
                "required": ["ip"],
            },
            "example": {"ip": "8.8.8.8"},
        },
    },
    "/api/v1/status": {
        "type": "http",
        "method": "GET",
        "input": {
            "type": "query",
            "schema": {
                "type": "object",
                "properties": {
                    "url": {"type": "string",
                            "description": "URL to check (http:// or https://)"},
                    "previous_hash": {"type": "string",
                                      "description": "sha256 of the body from an earlier call, to detect content drift"},
                },
                "required": ["url"],
            },
            "example": {"url": "https://example.com"},
        },
    },
    "/api/v1/nano-info": {
        "type": "http",
        "method": "GET",
        "input": {
            "type": "query",
            "schema": {
                "type": "object",
                "properties": {
                    "account": {"type": "string",
                                "description": "Nano account address to look up (nano_...)"},
                },
                "required": ["account"],
            },
            "example": {"account": "nano_3t6k35gi95xu6tergt6p69ck76ogmitsa8mnijtpxm9fkcm736xtoncuohr3"},
        },
    },
    "/api/v1/youtube-transcript": {
        "type": "http",
        "method": "GET",
        "input": {
            "type": "query",
            "schema": {
                "type": "object",
                "properties": {
                    "url": {"type": "string",
                            "description": "YouTube video URL to extract a transcript from"},
                    "language": {"type": "string",
                                 "description": "Language code for captions (default: en)"},
                },
                "required": ["url"],
            },
            "example": {"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ", "language": "en"},
        },
    },
    "/api/v1/mcp-find": {
        "type": "http",
        "method": "GET",
        "input": {
            "type": "query",
            "schema": {
                "type": "object",
                "properties": {
                    "q": {"type": "string",
                          "description": "Natural-language query — what the MCP/x402 service does"},
                    "limit": {"type": "integer",
                               "description": "Max results to return (1-50), default 10"},
                    "filter_rail": {"type": "string",
                                    "description": "Rail filter — e.g. 'nano' to show only XNO-settling services"},
                },
                "required": ["q"],
            },
            "example": {"q": "web scraping", "filter_rail": "nano"},
        },
    },
    "/api/v1/pdf-extract": {
        "type": "http",
        "method": "GET",
        "input": {
            "type": "query",
            "schema": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "format": "uri",
                            "description": "URL of a PDF to extract text from"},
                },
                "required": ["url"],
            },
            "example": {"url": "https://arxiv.org/pdf/1706.03762"},
        },
    },
    "/api/v1/hn-news": {
        "type": "http",
        "method": "GET",
        "input": {
            "type": "query",
            "schema": {
                "type": "object",
                "properties": {
                    "list": {"type": "string",
                             "description": "HN feed: top|new|best|ask|show|job"},
                    "limit": {"type": "integer",
                              "description": "Max stories to return (default 10, cap 30)"},
                    "score": {"type": "integer",
                              "description": "Optional minimum score filter"},
                },
            },
            "example": {"list": "top", "limit": 5},
        },
    },
    "/api/v1/address-verdict": {
        "type": "http",
        "method": "GET",
        "input": {
            "type": "query",
            "schema": {
                "type": "object",
                "properties": {
                    "account": {"type": "string",
                                "description": "Nano address (nano_ or xrb_ prefix) to classify"},
                },
                "required": ["account"],
            },
            "example": {"account": "nano_1yo6c1t64ahfjdw1dxizmbbnpdmbrckwhw9phbg5pdkeubrizga4qhnjmnx7"},
        },
    },
    "/api/v1/select": {
        "type": "http",
        "method": "GET",
        "input": {
            "type": "query",
            "schema": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "format": "uri",
                            "description": "Public URL to extract from"},
                    "selector": {"type": "string",
                                 "description": "CSS selector (e.g. h1, .price, table tr)"},
                    "attr": {"type": "string",
                             "description": "Optional attribute to read instead of text (e.g. href, src)"},
                    "limit": {"type": "integer",
                              "description": "Max matches to return (default 50, cap 200)"},
                },
                "required": ["url", "selector"],
            },
            "example": {"url": "https://example.com", "selector": "h1"},
        },
    },
    "/api/v1/links": {
        "type": "http",
        "method": "GET",
        "input": {
            "type": "query",
            "schema": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "format": "uri",
                            "description": "Public URL to extract links from"},
                    "limit": {"type": "integer",
                              "description": "Max links to return (default 200, cap 1000)"},
                },
                "required": ["url"],
            },
            "example": {"url": "https://example.com"},
        },
    },
    "/api/v1/meta": {
        "type": "http",
        "method": "GET",
        "input": {
            "type": "query",
            "schema": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "format": "uri",
                            "description": "Public URL to read page metadata from"},
                },
                "required": ["url"],
            },
            "example": {"url": "https://example.com/article"},
        },
    },
    "/api/v1/table": {
        "type": "http",
        "method": "GET",
        "input": {
            "type": "query",
            "schema": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "format": "uri",
                            "description": "Public URL to extract HTML tables from"},
                },
                "required": ["url"],
            },
            "example": {"url": "https://example.com/prices"},
        },
    },
    "/api/v1/wiki-summary": {
        "type": "http",
        "method": "GET",
        "input": {
            "type": "query",
            "schema": {
                "type": "object",
                "properties": {
                    "q": {"type": "string",
                          "description": "Entity or topic to look up (e.g. 'Nano', 'OpenAI', 'Python')"},
                },
                "required": ["q"],
            },
            "example": {"q": "Nano cryptocurrency"},
        },
    },
    "/api/v1/arxiv-paper": {
        "type": "http",
        "method": "GET",
        "input": {
            "type": "query",
            "schema": {
                "type": "object",
                "properties": {
                    "arxiv_id": {"type": "string",
                                 "description": "arXiv paper ID, e.g. '2106.09685'"},
                    "query": {"type": "string",
                              "description": "Full-text search terms (used when arxiv_id is absent)"},
                    "max_results": {"type": "integer",
                                    "description": "Max results for a free-text query (1-5)"},
                },
            },
            "example": {"arxiv_id": "2106.09685"},
        },
    },
    "/api/v1/batch-status": {
        "type": "http",
        "method": "GET",
        "input": {
            "type": "query",
            "schema": {
                "type": "object",
                "properties": {
                    "urls": {"type": "string",
                             "description": "Comma-separated list of URLs to health-check (1-50)"},
                    "method": {"type": "string",
                               "description": "HTTP method: HEAD (fast, default) or GET"},
                },
                "required": ["urls"],
            },
            "example": {"urls": "https://example.com,https://httpbin.org/status/200"},
        },
    },
    "/api/v1/screenshot": {
        "type": "http",
        "method": "GET",
        "input": {
            "type": "query",
            "schema": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "format": "uri",
                            "description": "Public URL to capture a screenshot of"},
                    "format": {"type": "string",
                               "description": "Image format: png or jpeg (default png)"},
                    "full_page": {"type": "boolean",
                                  "description": "Capture full scrollable page (default true)"},
                    "width": {"type": "integer",
                              "description": "Viewport width in pixels, 320-3840 (default 1280)"},
                    "height": {"type": "integer",
                               "description": "Viewport height in pixels, 240-2160 (default 720)"},
                },
                "required": ["url"],
            },
            "example": {"url": "https://example.com", "format": "png", "full_page": True},
        },
    },
    "/api/v1/render": {
        "type": "http",
        "method": "GET",
        "input": {
            "type": "query",
            "schema": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "format": "uri",
                            "description": "Public URL to render in a headless browser"},
                    "max_chars": {"type": "integer",
                                  "description": "Cap on the markdown returned, 100-500000 (default 200000)"},
                },
                "required": ["url"],
            },
            "example": {"url": "https://example.com", "max_chars": 200000},
        },
    },
}


def endpoint_input_spec(endpoint_path: str) -> dict:
    """What a buyer must send *before* paying, per endpoint."""
    return INPUT_SPECS.get(endpoint_path, {})


def build_openapi_spec(bases, prices):
    """OpenAPI 3.1 discovery spec for x402scan and agent directory crawlers.

    Follows the x402scan DISCOVERY.md spec:
    - x-payment-info on each paid operation
    - 402 response declared
    - price in USD decimal (runtime challenge carries raw units)

    ``bases`` maps endpoint name -> public base URL (extract, check, domain,
    search, geoip, nano). ``prices`` maps endpoint name -> price in XNO
    (extract, domain, websearch, geoip, nano).
    """
    EXTRACT_BASE = bases["extract"]
    CHECK_BASE = bases["check"]
    DOMAIN_BASE = bases["domain"]
    SEARCH_BASE = bases["search"]
    GEO_BASE = bases["geoip"]
    NANO_BASE = bases["nano"]
    YT_BASE = bases["youtube"]
    PDF_BASE = bases["pdf"]
    PRICE_XNO = prices["extract"]
    PRICE_DOMAIN_XNO = prices["domain"]
    PRICE_WEBSEARCH_XNO = prices["websearch"]
    PRICE_GEO_XNO = prices["geoip"]
    PRICE_NANO_XNO = prices["nano"]
    PRICE_YT_XNO = prices["youtube"]
    PRICE_PDF_XNO = prices["pdf"]

    price_usd = f"{PRICE_XNO:.6f}"
    return {
        "openapi": "3.1.0",
        "info": {
            "title": "Vend API Merchant",
            "version": "0.1.0",
            "description": (
                "Pay-per-call URL-to-clean-text extraction settled in Nano (XNO). "
                "No signup, no API keys. Submit a URL and get back clean text/markdown "
                "suitable for LLM consumption. Pay 0.0001 XNO per call via x402."
            ),
            "contact": {
                "email": "vend@paypercall.dev"
            },
            "x-guidance": (
                "Use GET /api/v1/extract with a ?url= parameter to fetch and clean "
                "a web page. The endpoint returns 402 Payment Required with an x402 v2 "
                "challenge; pay the quoted Nano amount and retry with X-PAYMENT header "
                "containing the block hash."
            ),
        },
        "servers": [
            {"url": EXTRACT_BASE, "description": "URL Extraction API"},
            {"url": CHECK_BASE, "description": "Link Checker API"},
            {"url": DOMAIN_BASE, "description": "Domain Intelligence API"},
            {"url": SEARCH_BASE, "description": "Web Search API"},
            {"url": GEO_BASE, "description": "IP Geolocation API"},
            {"url": NANO_BASE, "description": "Nano Account Info API"},
            {"url": YT_BASE, "description": "YouTube Transcript API"},
            {"url": PDF_BASE, "description": "PDF Text Extraction API"},
        ],
        "paths": {
            "/api/v1/extract": {
                "get": {
                    "operationId": "extractUrl",
                    "summary": "Extract clean text from a URL",
                    "tags": ["Extraction"],
                    "x-payment-info": {
                        "price": {
                            "mode": "fixed",
                            "currency": "USD",
                            "amount": price_usd,
                        },
                        "protocols": [{"x402": {}}],
                    },
                    "parameters": [
                        {
                            "name": "url",
                            "in": "query",
                            "required": True,
                            "schema": {
                                "type": "string",
                                "format": "uri",
                                "minLength": 1,
                                "description": "URL to extract clean text from",
                            },
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "Successful extraction",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "url": {"type": "string"},
                                            "title": {"type": "string"},
                                            "text": {"type": "string"},
                                            "markdown": {"type": "string"},
                                            "error": {"type": ["string", "null"]},
                                            "payment": {
                                                "type": "object",
                                                "properties": {
                                                    "amount_xno": {"type": "string"},
                                                    "block_hash": {"type": "string"},
                                                    "source": {"type": "string"},
                                                },
                                            },
                                            "receipt": {"type": "string"},
                                        },
                                    }
                                }
                            },
                        },
                        "402": {
                            "description": "Payment Required"
                        },
                    },
                }
            },
            "/api/v1/check-link": {
                "get": {
                    "operationId": "checkLink",
                    "summary": "Check HTTP status of a URL",
                    "tags": ["Utility"],
                    "x-payment-info": {
                        "price": {
                            "mode": "fixed",
                            "currency": "USD",
                            "amount": price_usd,
                        },
                        "protocols": [{"x402": {}}],
                    },
                    "parameters": [
                        {
                            "name": "url",
                            "in": "query",
                            "required": True,
                            "schema": {
                                "type": "string",
                                "format": "uri",
                                "minLength": 1,
                                "description": "URL to check",
                            },
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "Successful link check",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "url": {"type": "string"},
                                            "status_code": {"type": "integer"},
                                            "response_time_ms": {"type": "integer"},
                                            "final_url": {"type": "string"},
                                            "redirect_chain": {"type": "array"},
                                            "content_type": {"type": "string"},
                                            "content_length": {"type": "string"},
                                            "error": {"type": ["string", "null"]},
                                            "payment": {
                                                "type": "object",
                                                "properties": {
                                                    "amount_xno": {"type": "string"},
                                                    "block_hash": {"type": "string"},
                                                    "source": {"type": "string"},
                                                },
                                            },
                                            "receipt": {"type": "string"},
                                        },
                                    }
                                }
                            },
                        },
                        "402": {
                            "description": "Payment Required"
                        },
                    },
                }
            },
            "/api/v1/domain-info": {
                "get": {
                    "operationId": "domainInfo",
                    "summary": "Full domain intelligence: DNS, WHOIS, SSL",
                    "tags": ["Data"],
                    "x-payment-info": {
                        "price": {
                            "mode": "fixed",
                            "currency": "USD",
                            "amount": f"{PRICE_DOMAIN_XNO:.6f}",
                        },
                        "protocols": [{"x402": {}}],
                    },
                    "parameters": [
                        {
                            "name": "domain",
                            "in": "query",
                            "required": True,
                            "schema": {
                                "type": "string",
                                "minLength": 1,
                                "description": "Domain name to look up (e.g. example.com)",
                            },
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "Successful domain info response",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "domain": {"type": "string"},
                                            "resolved_ip": {"type": "string"},
                                            "dns": {"type": "object"},
                                            "whois": {"type": "object"},
                                            "ssl": {"type": "object"},
                                            "http_headers": {"type": "object"},
                                            "lookup_time_ms": {"type": "integer"},
                                            "error": {"type": ["string", "null"]},
                                            "payment": {
                                                "type": "object",
                                                "properties": {
                                                    "amount_xno": {"type": "string"},
                                                    "block_hash": {"type": "string"},
                                                    "source": {"type": "string"},
                                                },
                                            },
                                            "receipt": {"type": "string"},
                                        },
                                    }
                                }
                            },
                        },
                        "402": {
                            "description": "Payment Required"
                        },
                    },
                }
            },
            "/api/v1/web-search": {
                "get": {
                    "operationId": "webSearch",
                    "summary": "Web search via DuckDuckGo",
                    "x-payment-info": {
                        "price": {
                            "mode": "fixed",
                            "currency": "USD",
                            "amount": f"{PRICE_WEBSEARCH_XNO:.6f}",
                        },
                        "protocols": [{"x402": {}}],
                    },
                    "parameters": [
                        {
                            "name": "q",
                            "in": "query",
                            "required": True,
                            "schema": {"type": "string"},
                            "description": "Search query",
                        },
                    ],
                    "responses": {
                        "200": {
                            "description": "Search results",
                        },
                        "402": {
                            "description": "Payment Required",
                        },
                    },
                }
            },
            "/api/v1/geoip": {
                "get": {
                    "operationId": "geoip",
                    "summary": "IP geolocation lookup",
                    "x-payment-info": {
                        "price": {
                            "mode": "fixed",
                            "currency": "USD",
                            "amount": f"{PRICE_GEO_XNO:.6f}",
                        },
                        "protocols": [{"x402": {}}],
                    },
                    "parameters": [
                        {
                            "name": "ip",
                            "in": "query",
                            "required": True,
                            "schema": {"type": "string"},
                            "description": "IP address to look up (or 'myip' for caller's IP)",
                        },
                    ],
                    "responses": {
                        "200": {
                            "description": "Successful geolocation lookup",
                        },
                        "402": {
                            "description": "Payment Required",
                        },
                    },
                }
            },
            "/api/v1/status": {
                "get": {
                    "operationId": "urlStatus",
                    "summary": "URL status, redirects, TLS expiry and content drift",
                    "x-payment-info": {
                        "price": {
                            "mode": "fixed",
                            "currency": "USD",
                            "amount": f"{PRICE_XNO:.6f}",
                        },
                        "protocols": [{"x402": {}}],
                    },
                    "parameters": [
                        {
                            "name": "url",
                            "in": "query",
                            "required": True,
                            "schema": {"type": "string"},
                            "description": "URL to check (http:// or https://)",
                        },
                        {
                            "name": "previous_hash",
                            "in": "query",
                            "required": False,
                            "schema": {"type": "string"},
                            "description": "sha256 of the body from an earlier call, to detect content drift",
                        },
                    ],
                    "responses": {
                        "200": {
                            "description": "Successful URL status check",
                        },
                        "402": {
                            "description": "Payment Required",
                        },
                    },
                }
            },
            "/api/v1/nano-info": {
                "get": {
                    "operationId": "nanoInfo",
                    "summary": "Nano account intelligence",
                    "x-payment-info": {
                        "price": {
                            "mode": "fixed",
                            "currency": "USD",
                            "amount": f"{PRICE_NANO_XNO:.6f}",
                        },
                        "protocols": [{"x402": {}}],
                    },
                    "parameters": [
                        {
                            "name": "account",
                            "in": "query",
                            "required": True,
                            "schema": {"type": "string"},
                            "description": "Nano account address to look up (nano_...)",
                        },
                    ],
                    "responses": {
                        "200": {
                            "description": "Successful Nano account info lookup",
                        },
                        "402": {
                            "description": "Payment Required",
                        },
                    },
                }
            },
            "/api/v1/youtube-transcript": {
                "get": {
                    "operationId": "youtubeTranscript",
                    "summary": "Extract captions/transcript from a YouTube video",
                    "x-payment-info": {
                        "price": {
                            "mode": "fixed",
                            "currency": "USD",
                            "amount": f"{PRICE_YT_XNO:.6f}",
                        },
                        "protocols": [{"x402": {}}],
                    },
                    "parameters": [
                        {
                            "name": "url",
                            "in": "query",
                            "required": True,
                            "schema": {"type": "string"},
                            "description": "YouTube video URL to extract a transcript from",
                        },
                        {
                            "name": "language",
                            "in": "query",
                            "required": False,
                            "schema": {"type": "string"},
                            "description": "Language code for captions (default: en)",
                        },
                    ],
                    "responses": {
                        "200": {
                            "description": "Successful transcript extraction",
                        },
                        "402": {
                            "description": "Payment Required",
                        },
                    },
                }
            },
            "/api/v1/pdf-extract": {
                "get": {
                    "operationId": "pdfExtract",
                    "summary": "Extract text from a PDF at a URL",
                    "tags": ["Extraction"],
                    "x-payment-info": {
                        "price": {
                            "mode": "fixed",
                            "currency": "USD",
                            "amount": f"{PRICE_PDF_XNO:.6f}",
                        },
                        "protocols": [{"x402": {}}],
                    },
                    "parameters": [
                        {
                            "name": "url",
                            "in": "query",
                            "required": True,
                            "schema": {
                                "type": "string",
                                "format": "uri",
                                "minLength": 1,
                                "description": "URL of a PDF to extract text from",
                            },
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "Successful PDF text extraction (title, page_count, page-structured text)",
                        },
                        "402": {
                            "description": "Payment Required",
                        },
                    },
                }
            },
            "/.well-known/x402": {
                "get": {
                    "operationId": "x402Manifest",
                    "summary": "x402 capability manifest",
                    "tags": ["Discovery"],
                    "responses": {
                        "200": {
                            "description": "x402 v2 capability manifest",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                    }
                                }
                            },
                        }
                    },
                }
            },
            "/.well-known/agent-tools.json": {
                "get": {
                    "operationId": "agentToolsManifest",
                    "summary": "Agent-tools.cloud discovery manifest",
                    "tags": ["Discovery"],
                    "responses": {
                        "200": {
                            "description": "Agent-tools discovery manifest",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                    }
                                }
                            },
                        }
                    },
                }
            },
            "/health": {
                "get": {
                    "operationId": "health",
                    "summary": "Health check",
                    "tags": ["System"],
                    "responses": {
                        "200": {
                            "description": "Server is healthy",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "status": {"type": "string"},
                                            "service": {"type": "string"},
                                            "version": {"type": "string"},
                                        },
                                    }
                                }
                            },
                        }
                    },
                }
            },
        },
        "x-discovery": {
            "ownershipProofs": [],
        },
    }


# ── One list: every discovery surface is derived from the x402 manifest ──────
#
# Issue #461: /openapi.json listed 9 paid paths, llms.txt and agent-tools.json
# missed others, while /.well-known/x402 listed 23. Each surface kept its own
# hand-written list and they drifted. The x402 manifest's ``resources`` is the
# single source of truth for what is paid and live; the helpers below turn it
# into the OpenAPI paths, the llms.txt endpoint table and the agent-tools list,
# so adding an endpoint to the manifest adds it everywhere and nothing else can.

RAW_PER_XNO = 10 ** 30


def raw_to_xno(raw) -> str:
    """Raw units -> plain XNO decimal string (10**26 -> '0.0001')."""
    from decimal import Decimal
    d = Decimal(int(raw)) / Decimal(RAW_PER_XNO)
    s = format(d.normalize(), "f")
    return s


def paid_from_manifest(manifest: dict) -> list:
    """The paid catalogue, in manifest order, as flat records.

    Only entries that carry an ``accepts`` list are paid; free endpoints live
    under the manifest's ``free`` key and are never included here.
    """
    from urllib.parse import urlsplit
    out = []
    for r in manifest.get("resources", []):
        accepts = r.get("accepts") or []
        if not accepts:
            continue
        parts = urlsplit(r["url"])
        a = accepts[0]
        out.append({
            "path": parts.path,
            "url": r["url"],
            "base": f"{parts.scheme}://{parts.netloc}",
            "method": (r.get("method") or "GET").upper(),
            "description": r.get("description", ""),
            "amount_raw": str(a["amount"]),
            "price_xno": raw_to_xno(a["amount"]),
            "pay_to": a["payTo"],
        })
    return out


def _first_sentence(text: str, limit: int = 140) -> str:
    s = (text or "").split(". ")[0].strip().rstrip(".")
    return s if len(s) <= limit else s[: limit - 1].rstrip() + "…"


def _operation_id(path: str, method: str) -> str:
    words = [w for w in path.replace("/api/v1/", "").replace("/", "-").split("-") if w]
    name = words[0] + "".join(w.capitalize() for w in words[1:]) if words else "op"
    return name if method == "GET" else f"{method.lower()}{name[0].upper()}{name[1:]}"


def _generated_operation(item: dict) -> dict:
    spec = INPUT_SPECS.get(item["path"], {})
    schema = (spec.get("input") or {}).get("schema") or {}
    required = set(schema.get("required") or [])
    params = []
    for name, prop in (schema.get("properties") or {}).items():
        params.append({
            "name": name,
            "in": "query",
            "required": name in required,
            "schema": prop,
        })
    op = {
        "operationId": _operation_id(item["path"], item["method"]),
        "summary": _first_sentence(item["description"]),
        "description": item["description"],
        "tags": ["Paid"],
        "servers": [{"url": item["base"]}],
        "x-payment-info": {
            "price": {"mode": "fixed", "currency": "USD",
                      "amount": f"{float(item['price_xno']):.6f}"},
            "protocols": [{"x402": {}}],
        },
        "responses": {
            "200": {"description": "Successful response",
                    "content": {"application/json": {"schema": {"type": "object"}}}},
            "402": {"description": "Payment Required"},
        },
    }
    if params:
        op["parameters"] = params
    return op


def complete_openapi(spec: dict, paid: list) -> dict:
    """Make the OpenAPI ``paths`` exactly the paid catalogue.

    Hand-written operations (richer response schemas) are kept when they
    exist; every other paid path gets an operation generated from the manifest
    entry and its INPUT_SPECS. /api/v1 paths the manifest does not sell are
    dropped, so the paid set can never differ from /.well-known/x402.
    """
    old = spec.get("paths", {})
    paths = {k: v for k, v in old.items() if not k.startswith("/api/v1/")}
    for item in paid:
        m = item["method"].lower()
        existing = (old.get(item["path"]) or {}).get(m)
        paths.setdefault(item["path"], {})[m] = existing or _generated_operation(item)
    spec["paths"] = paths
    known = {s.get("url") for s in spec.get("servers", [])}
    for item in paid:
        if item["base"] not in known:
            spec.setdefault("servers", []).append({"url": item["base"]})
            known.add(item["base"])
    return spec


def _example_url(item: dict) -> str:
    from urllib.parse import urlencode
    ex = ((INPUT_SPECS.get(item["path"], {}).get("input") or {}).get("example")) or {}
    return f"{item['url']}?{urlencode(ex, safe=':/,')}" if ex and item["method"] == "GET" else item["url"]


def llms_endpoint_table(paid: list) -> str:
    """The llms.txt endpoint table, one row per paid manifest resource."""
    rows = [
        "| Name | Method | URL | Price (XNO) | Description |",
        "|------|--------|-----|-------------|-------------|",
    ]
    for item in paid:
        name = item["path"].replace("/api/v1/", "")
        desc = _first_sentence(item["description"]).replace("|", "/")
        rows.append(f"| {name} | {item['method']} | `{_example_url(item)}` | "
                    f"{item['price_xno']} | {desc} |")
    return "\n".join(rows)


def agent_tools_paid(paid: list) -> list:
    """agent-tools.json resource entries for every paid manifest resource."""
    return [{
        "path": item["path"],
        "url": item["url"],
        "method": item["method"],
        "description": item["description"],
        "price_xno": float(item["price_xno"]),
        "price_raw": item["amount_raw"],
        "pay_to": item["pay_to"],
    } for item in paid]
