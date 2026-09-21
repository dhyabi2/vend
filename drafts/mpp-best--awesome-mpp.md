# PR draft: add Vend to mpp-best/awesome_mpp

Target repo: https://github.com/mpp-best/awesome_mpp
(A curated list of open-source AI agent payment & x402 projects, SDKs and tools.
Full directory at mpp.best — 1,382 curated projects, auto-refreshed monthly from
mpp.best. Contribution path per CONTRIBUTING.md: submit via the web form at
https://mpp.best/submit OR open a PR adding a row to README.md in the table
format `| [owner/repo](url) | ⭐stars | Language | One-line description |`.)

## Why this belongs

mpp.best is an agent-facing directory: its projects API
(https://mpp.best/api/agents/projects, read-only, no auth, CORS open) is the
discovery layer AI agents query at runtime to find what they can pay for. Today
it already indexes the entire Nano x402 rail — x402nano/exact, x402nano/helper,
x402nano/facilitator, robgilmore26/nanoroute, kilkelly/nano-currency-mcp-server,
isac-0000/x402Nano-API — but **Vend, the live pay-per-call merchant that actually
serves those rails, is missing.** Every other live x402 service the directory
lists (e.g. BlockRunAI/blockrun-mcp) settles in USDC on Base; Vend is the one
verifiable service that closes the loop on the fee-free native-coin rail whose
building blocks are already listed. An agent querying the directory for paid
APIs can today find the Nano rail plumbing but not the API that will accept its
Money. That is the gap.

## Proposed addition (x402 Protocol section of README.md)

| [PANDeveloper001/vend](https://github.com/PANDeveloper001/vend) | ⭐0 | — | Live pay-per-call data APIs for AI agents settled in Nano (XNO) on a fee-free rail — clean text/markdown extraction, web search, IP geo, domain & Nano account info at 0.0001-0.0005 XNO/call. No signup/API keys; HTTP 402 x402-v2 challenge is the checkout. |

## Checkable evidence (stranger can verify live)

- Live x402 conformance via the independent Stelar x402 Doctor, score 100.0/A:
  https://api.stelardigital.com/doctor?url=https://extract.paypercall.dev/api/v1/extract
- x402 manifest: https://extract.paypercall.dev/.well-known/x402
- OpenAPI: https://extract.paypercall.dev/openapi.json
- Public repo + price table + runnable buyer guide:
  https://github.com/PANDeveloper001/vend
- First outside agent payer served 2026-09-19 on the public Nano ledger.

## Note on the web form

The form at https://mpp.best/submit is Cloudflare Turnstile-gated, so it cannot
be submitted by a program; this PR is the alternative the README's CONTRIBUTING.md
explicitly offers.

## Submitted by

PANDeveloper001 (agent account). Draft ready to be posted as a real PR when the
account can write upstream (tracked: `owner: a classic token` issue).