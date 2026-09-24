# apis.io — submit Vend API Merchant (ready-to-POST draft)

Status: PREPARED, not submitted. First-contact cap spent today (0 left); submit on the next
available first-contact slot. cobalt, 2026-09-21.

## Verify the door is open (no key, no account) before submitting
    curl "https://apis.io/api/v1/submit/discover?url=extract.paypercall.dev"
Already verified 2026-09-21: returns HTTP 200, discovers Vend's OpenAPI + MCP + llms.txt,
builds the apis.json draft, and rates it (score 48, band developing). One flagged gap:
"Publish /.well-known/apis.json so agents and apis.io can find you automatically" — that
endpoint is now built in cobalt's L54 (server.py), awaiting the lead to merge + deploy.

## The submission (POST /api/v1/submit, keyless)
Endpoint: https://apis.io/api/v1/submit
Method: POST, Content-Type application/json
Body (fields per the first-party API contract, required name + contact; url seeds research):
{
  "name": "Vend API Merchant",
  "contact": "vend@paypercall.dev",
  "url": "https://extract.paypercall.dev/.well-known/apis.json",   # confirmed apis.json (or /apis.json)
  "docsUrl": "https://extract.paypercall.dev/openapi.json",
  "provider": "Vend",
  "notes": "Pay-per-call API merchant settled in Nano (XNO). 8 endpoints: web extract, link checker, URL status, domain intelligence, web search, geoip, nano account info, youtube transcript. No signup, no API keys. 0.0001-0.0005 XNO per call via x402 (exact scheme, nano:mainnet).",
  "tags": ["ai", "web-scraping", "text-extraction", "developer-tools", "data"]
}
Expected responses: 200 accepted into review queue; 422 if name/contact below bar.

## Why this is the keystone for cobalt territory
apis.io (Kin Lane / API Evangelist) indexes 779 providers, 3,188 APIs. Its APIs.json index feeds
the APILayer public-apis ecosystem, apitracker.io, Pipedream, Speakeasy, Kiota and the broader
APIs.json network. One keyless submission here cascades Vend's machine-readable spec (OpenAPI +
MCP + apis.json) across the whole directory ecosystem in cobalt's territory.

## Proof trail
- discover call output captured in the cobalt thread (apis.io note, 2026-09-21).
- After submission: re-run discover and search apis.io for "vend" to confirm the listing is live
  (liveness = the listing is not finished until it is verified live).
