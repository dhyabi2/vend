# Vend — Autonomous API Merchant

Pay-per-call APIs settled in Nano (XNO). No signup, no API keys — just HTTP 402 with an x402 v2 challenge.

---

## Endpoints

| Endpoint | Price (XNO) | What it does |
|---|---|---|
| `GET /api/v1/extract?url=` | 0.0001 | Extract clean text/markdown from any web page |
| `GET /api/v1/check-link?url=` | 0.0001 | Check HTTP status, response time, redirect chain |
| `GET /api/v1/status?url=&previous_hash=` | 0.0001 | URL status, redirects, TLS expiry and content drift |
| `GET /api/v1/domain-info?domain=` | 0.0005 | Full domain intelligence: DNS, WHOIS, SSL, HTTP headers |
| `GET /api/v1/web-search?q=` | 0.0001 | Web search via DuckDuckGo — titles, URLs, snippets |
| `GET /api/v1/geoip?ip=` | 0.0001 | IP geolocation — country, city, coordinates, ISP, ASN |
| `GET /api/v1/nano-info?account=` | 0.0005 | Nano account intelligence — balance, representative, block count, frontier, weight, pending |
| `GET /api/v1/youtube-transcript?url=` | 0.0005 | Captions/transcript from a YouTube video |
| `GET /api/v1/select?url=&selector=` | 0.0001 | CSS-selector structured field extraction from a page (prices, headings, links) |
| `GET /api/v1/links?url=` | 0.0001 | Extract every anchor link on a page as structured JSON (crawl, audit, sitemap) |
| `GET /api/v1/pdf-extract?url=` | 0.0005 | Extract text from a PDF URL, page-structured, ready for LLM consumption |

## Quick buyer guide

> **[BUYERS_GUIDE.md](BUYERS_GUIDE.md)** — full step-by-step walkthrough with curl, Python, JavaScript, and wallet instructions.  
> The short version: call any endpoint -> get 402 -> send Nano -> retry with block hash.

## How it works (buyer flow)

```
1. GET /api/v1/extract?url=https://example.com
   → HTTP 402 with x402 payment challenge

2. Send 0.0001 XNO to nano_1yo6c1t64ahfjdw1dxizmbbnpdmbrckwhw9phbg5pdkeubrizga4qhnjmnx7
   → Get back a 64-char block hash

3. GET /api/v1/extract?url=https://example.com  -H "X-PAYMENT: <block-hash>"
   → HTTP 200 with the extracted text
```

### Python example

```python
import httpx

# Step 1: Probe unpaid
resp = httpx.get("https://search.paypercall.dev/api/v1/web-search?q=nano")
assert resp.status_code == 402
challenge = resp.json()

# Step 2: Extract payment info
accept = challenge["accepts"][0]
print(f"Pay {challenge['price_xno']} XNO to {accept['payTo'][:15]}...")

# Step 3: Send Nano payment, get block hash (use your wallet)
# Step 4: Retry with payment
result = httpx.get(
    "https://search.paypercall.dev/api/v1/web-search?q=nano",
    headers={"X-PAYMENT": "your-64-char-block-hash"}
)
print(result.json())
```

See `examples/python-buyer.py` for a full working script with error handling.

## Conformance

All endpoints pass the Stelar x402 Doctor at 100.0/A:

- extract: [https://api.stelardigital.com/doctor?url=https://extract.paypercall.dev/api/v1/extract](https://api.stelardigital.com/doctor?url=https://extract.paypercall.dev/api/v1/extract)
- check-link: [https://api.stelardigital.com/doctor?url=https://check.paypercall.dev/api/v1/check-link](https://api.stelardigital.com/doctor?url=https://check.paypercall.dev/api/v1/check-link)
- domain-info: [https://api.stelardigital.com/doctor?url=https://domain.paypercall.dev/api/v1/domain-info](https://api.stelardigital.com/doctor?url=https://domain.paypercall.dev/api/v1/domain-info)
- web-search: [https://api.stelardigital.com/doctor?url=https://search.paypercall.dev/api/v1/web-search](https://api.stelardigital.com/doctor?url=https://search.paypercall.dev/api/v1/web-search)
- geoip: [https://api.stelardigital.com/doctor?url=https://geoip.paypercall.dev/api/v1/geoip](https://api.stelardigital.com/doctor?url=https://geoip.paypercall.dev/api/v1/geoip)
- nano-info: `https://extract.paypercall.dev/api/v1/nano-info` (nano.paypercall.dev DNS is still pointing at a dead deployment, so every advertised URL names this host)

x402 v2 challenge in both header and body. Per-endpoint subdomains. Bazaar input schema on every endpoint.

## Discovery

- x402 manifest: `https://extract.paypercall.dev/.well-known/x402` (also at check, domain, search)
- OpenAPI spec: `https://extract.paypercall.dev/openapi.json` (also at check, domain, search)
- agent-tools.cloud: [https://agent-tools.cloud/services/extract-paypercall-dev-sub822](https://agent-tools.cloud/services/extract-paypercall-dev-sub822)

## Running locally

```bash
# Our package is not on PyPI yet (the `vend` name on PyPI is an unrelated packaging tool).
# Run from this repo instead:
uv sync
export VEND_WALLET_ADDRESS="nano_..."
uv run python -m vend
```

## License

MIT