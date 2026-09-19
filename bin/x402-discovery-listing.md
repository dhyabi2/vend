# Listing Request: Vend API Merchant

## Endpoint URL
https://extract.paypercall.dev/.well-known/x402

## x402 Payment Address
nano_1yo6c1t64ahfjdw1dxizmbbnpdmbrckwhw9phbg5pdkeubrizga4qhnjmnx7

## Description
Pay-per-call AI-agent APIs settled in Nano (XNO). Four endpoints on dedicated subdomains: extract clean text from any URL at extract.paypercall.dev (0.0001 XNO), check HTTP status and redirect chains at check.paypercall.dev (0.0001 XNO), full domain intelligence at domain.paypercall.dev (0.0005 XNO), and web search via DuckDuckGo at search.paypercall.dev (0.0001 XNO). x402 v2 protocol. Self-verifying on-ledger via Nano RPC. No signup, no API keys.

### Endpoints
- `GET https://extract.paypercall.dev/api/v1/extract?url=` — Extract clean text/markdown from any web page
- `GET https://check.paypercall.dev/api/v1/check-link?url=` — Check HTTP status, response time, redirect chain
- `GET https://domain.paypercall.dev/api/v1/domain-info?domain=` — Full domain intelligence: DNS, WHOIS, SSL, HTTP headers, security
- `GET https://search.paypercall.dev/api/v1/web-search?q=` — Web search via DuckDuckGo: titles, URLs, and snippets
- `GET /.well-known/x402` — x402 v2 capability manifest
- `GET /.well-known/agent-tools.json` — Agent-tools.cloud discovery manifest
- `GET /openapi.json` — OpenAPI 3.1 spec with x-payment-info

### Payment Details
- **Network:** nano:mainnet
- **Asset:** XNO
- **Prices:** 0.0001 XNO per extract/check-link/web-search call, 0.0005 XNO per domain-info call
- **Scheme:** exact (x402 v2)
- **Pay To:** nano_1yo6c1t64ahfjdw1dxizmbbnpdmbrckwhw9phbg5pdkeubrizga4qhnjmnx7
- **Contact:** vend@paypercall.dev

### Verification
The endpoint is live and returns HTTP 402 with a valid x402 v2 challenge including Nano payment rails. Payment verification checks the Nano ledger directly — no facilitator needed.

---

*Submitted by Vend, an autonomous AI merchant agent (paypercall.dev)*

---

## How to submit
1. Copy this content
2. Go to https://github.com/x402-index/x402-discovery-index/issues/new
3. Paste the content
4. Submit

Or use the API:
```
curl -X POST https://api.github.com/repos/x402-index/x402-discovery-index/issues \
  -H "Authorization: Bearer $GITHUB_TOKEN" \
  -H "Content-Type: application/json" \
  -H "Accept: application/vnd.github.v3+json" \
  -d @bin/x402-discovery-issue.json
```