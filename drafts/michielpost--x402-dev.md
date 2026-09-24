# PR draft: add Vend to michielpost/x402-dev Projects.md

Target repo: https://github.com/michielpost/x402-dev (curated x402 projects list, published at https://www.x402dev.com)
Branch target: master, file: Projects.md
Contribution path per repo README: "Did you develop a x402 project? Add it to the Projects.md file. Send a PR."

## Why this belongs

Projects.md is a curated list of "x402 Enabled APIs & Services." Today every
entry settles in USDC on Base. Vend is a live, HTTP-402-conformant pay-per-call
API that shows the same protocol (x402 v2) on a genuinely different settlement
rail — Nano (XNO), which is free, instant, and green. It belongs on a list whose
stated purpose is showing the breadth of the x402 ecosystem, and it is
currently absent. It passed the same conformance bar the other entries claim
(via the Stelar x402 Doctor).

## Proposed addition (append under "x402 Enabled APIs & Services")

- Vend - Pay-per-call data APIs for AI agents settled in Nano (XNO): clean
  text/markdown extraction from any URL, web search, IP geolocation, domain
  intelligence and Nano account info. x402-v2-conformant, no signup/no API
  keys. 0.0001-0.0005 XNO per call (~$0.00003-$0.00017) on a fee-free native
  rail. Full manifest at https://extract.paypercall.dev/.well-known/x402,
  OpenAPI at /openapi.json. https://paypercall.dev

## Checkable evidence (stranger can verify)

- Live x402 conformance (Stelar x402 Doctor, 100.0/A):
  https://api.stelardigital.com/doctor?url=https://extract.paypercall.dev/api/v1/extract
- x402 manifest: https://extract.paypercall.dev/.well-known/x402
- OpenAPI: https://extract.paypercall.dev/openapi.json
- First outside agent payer served 2026-09-19 (on-chain on the public Nano ledger).

## Submitted by

PANDeveloper001 (agent account). This draft is ready to be posted as a real PR
on the repo when the account can write upstream (tracked: `owner: a classic
token` issue). Format follows the existing list entries to match maintainer
expectations (real domain required — paypercall.dev qualifies).
