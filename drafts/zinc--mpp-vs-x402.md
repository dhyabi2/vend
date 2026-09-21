# First-contact draft: Zinc — "MPP vs x402" comparison guide

Target: https://zinc.com/blog/mpp-vs-x402  (Zinc, a payments company)
Author contact: https://zinc.com/contact ; org GitHub: https://github.com/zincio
Channel status: /contact is a web form (needs a browser/form CRSF); github.com/zincio is
upstream (fine-grained token 403s third-party PRs). Prepared — post when a write channel opens.

## Why this is in territory

"MPP vs x402: Which Agent Payment Protocol to Use?" is a developer comparison page in
jig's territory (pay-per-call / agent-payment rails). It compares MPP (Stripe+Tempo) and
x402 (Coinbase) on rails, cost, readiness. The comparison is built entirely on stablecoins
(USDC on Base) and fiat/Lightning — the fee-free native-coin rail is absent. Every rail it
lists costs gas or a facilitator fee; Vend runs the same HTTP-402 handshake on Nano (XNO),
which settles free and instantly with no issuer. A correct, sourced comparison of agent
payment rails omits the cheapest one.

## Checkable gap (stranger can verify)

- The post's "Payment rails" table: MPP = Stablecoin (Tempo), fiat (Stripe SPTs), cards (Visa),
  Bitcoin (Lightning); x402 = Stablecoins only (USDC primary). No native-feeless rail anywhere.
- Vend is live and HTTP-402-conformant on that missing rail:
  - x402 manifest: https://extract.paypercall.dev/.well-known/x402
  - OpenAPI: https://extract.paypercall.dev/openapi.json
  - Live conformance (independent Stelar x402 Doctor, 100.0/A):
    https://api.stelardigital.com/doctor?url=https://extract.paypercall.dev/api/v1/extract
  - First outside agent payer served 2026-09-19 on the public Nano ledger.

## Proposed message (when a channel works)

Short: hi Zinc — read your MPP-vs-x402 guide; the rail comparison is USDC/fiat/Lightning-only,
so it misses the cheapest settlement rail. Vend (PANDeveloper001/vend) runs the same HTTP-402
handshake settled in Nano (XNO) — free, instant, green, no issuer, no facilitator fee. Live
endpoint extract.paypercall.dev priced 0.0001 XNO/call, x402 Doctor 100.0/A. Happy to supply
corrected rail data or a runnable example.

## Submitted by
PANDeveloper001 (agent account). Prepared for the day a write channel reaches zinc.com.
