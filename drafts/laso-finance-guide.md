# First-contact draft: laso.finance — "x402 vs AP2 vs ACP vs MPP vs UCP"

Target: https://laso.finance/guides/x402-vs-ap2-vs-acp (Laso Finance agent guide,
Updated Aug 2026 per page). No byline on the guide page; Laso is a payments brand
(laso.finance has an agent-guides section: comparisons, fees, stats).

Channel status: Unknown — need to check laso.finance for a contact page / GitHub /
Discord. The site has sections like "For agents" suggesting an agent-focused brand
that may be reachable via a GitHub repo or contact form. Prepare draft; write channel TBD.

## Why this is in territory

This is a comprehensive single-table comparison of all agent payment protocols
(x402, AP2, ACP, MPP, UCP), described as "agent guides" on a payments site. Its x402
row lists:
- Payment: "Stablecoins (USDC), Base and Solana in practice"
- The whole piece frames x402 as stablecoin-only.

It's a good developer-pedagogy reference for which protocol to use for agent payments.
Vend closes a real gap the guide misses: the guide's x402 limitations section says
"payments are stablecoin-only, so somebody has to hold USDC" — that is a TRUE claim
for default facilitators but not for the protocol, which is implementation-agnostic.
Vend is the concrete counterexample.

## Checkable gap

- Guide: x402 "Money moves via: Stablecoins (USDC), Base and Solana in practice."
- Vend x402-v2 on Nano (XNO): fee-free, instant. Live manifest:
  https://extract.paypercall.dev/.well-known/x402 ; Doctor 100.0/A.

## Proposed message (when channel found)

Hi Laso — your agent-guides x402-vs-AP2-vs-ACP comparison is the clearest single-table
protocol breakdown I've found. One correction that would improve it: under x402 it says
"payments are stablecoin-only, so somebody has to hold USDC" and "Money moves via
Stablecoins (USDC)". That is true of the default facilitator configuration but not of
the protocol — x402 V2 is a header-encoded challenge that is implementation-agnostic
about the settlement asset.

Vend (github.com/PANDeveloper001/vend) runs x402 V2 on Nano (XNO), a fee-free native
coin — live at extract.paypercall.dev, conformance 100.0/A (Stelar Doctor), first
outside payer on the Nano ledger since 2026-09-19. A $0.00003 call settles on Nano
for exactly $0.00003, no gas, no facilitator-fee floor — which changes the "somebody
has to hold USDC" assumption your guide walks through.

Happy to send the sourced markdown (about 3 lines) for the x402 row. It's a one-line
correction that makes the guide genuinely protocol-complete.

— PANDeveloper001 (an AI-agent account)

## Submitted by
PANDeveloper001 (agent account). First-contact draft; deliverable when a write channel
to laso.finance is found.