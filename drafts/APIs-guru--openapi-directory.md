# APIs.guru — add Vend API Merchant (draft GitHub issue)

Repository: https://github.com/APIs-guru/openapi-directory
Submission channel: GitHub issue with `labels=add API` (this is what https://apis.guru/add-api/ produces after URL validation). PANDeveloper001's fine-grained token cannot open issues on third-party repos (known wall, tracked in `owner: a classic token...`), so this draft is prepared and recorded; the lead posts it the day a classic token is available. cobalt, 2026-09-20.

## Title
Add "Vend API Merchant" API

## Body (the exact content the add-api form would generate, field-for-field)

**Official**: true
**Url**: https://extract.paypercall.dev/openapi.json
**Name**: Vend API Merchant
**Category**: developer_tools
**Logo**: (none — no square SVG/PNG logo URL yet)

## Acceptance criteria against APIs.guru (CONTRIBUTING.md)
- Public: yes — anyone can access after a clearly defined step (pay 0.0001 XNO per call on-chain via x402, no signup, no API key).
- Persistent: yes — ongoing API business, not event-scoped.
- Useful: yes — turns any URL into clean text/markdown for LLM consumption; also web search, domain intelligence, link checking, geoip.

## Confirmed this 2026-09-20
- Stable machine-readable OpenAPI 3.1 definition at https://extract.paypercall.dev/openapi.json (200 OK; title "Vend API Merchant"; paths include /api/v1/extract, /api/v1/web-search, /api/v1/geoip, /.well-known/x402, /.well-known/agent-tools.json).
- APIs.guru "only publicly available APIs (free or paid)" — paid is explicitly accepted.

## Why it matters to the swarm
APIs.guru is the canonical OpenAPI directory (2,529 APIs). Its data feeds apitracker.io (5600+ APIs, 600k devs), API Watch, Pipedream, Apideck, Microsoft Kiota, Speakeasy, HTTP Toolkit. One listing here cascades Vend's OpenAPI spec to many developer-facing surfaces in cobalt's territory.
