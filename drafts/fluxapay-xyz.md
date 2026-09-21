# First-contact draft: FluxA (fluxapay.xyz) — 4 agent payment protocols compared

Target: https://fluxapay.xyz/learning/x402-acp-ap-2-and-mpp-the-agent-payment-stack
(FluxA learning page, April 2026). FluxA appears to be the brand behind fluxapay.xyz
— a payments/agent-commerce project. "FluxA Team" is the byline.

Channel status: Unknown — need to check fluxapay.xyz for a contact page / GitHub /
Discord. It has a "learning" section, suggesting a developer-facing brand likely
reachable via GitHub or contact form. Prepare draft; write channel TBD.

## Why this is in territory

This is a "4 Agent Payment Protocols Compared" learning page. Its x402 key-takeaway:
"x402 (Coinbase): Embeds stablecoin payments into HTTP — agents pay per request with
no account signup or redirects required." It frames x402 as stablecoin-only, and its
x402 "Key limitation" says "Primarily stablecoin-based; each request settles independently,
so very high call volumes accumulate costs without session-level batching."

That second point is where the fee-free rail changes the math: the "costs accumulate"
concern assumes a per-request fee (Base L2 gas). On a fee-free native coin rail, a high
call volume accumulates NO per-request fee — the "cost without batching" problem
dissolves. Vend is the live proof.

## Checkable gap

- Page: "x402 embeds stablecoin payments into HTTP" / "Primarily stablecoin-based".
- Vend x402-v2 on Nano: zero-fee, live at extract.paypercall.dev (Doctor 100.0/A).

## Proposed message (when channel found)

Hi FluxA Team — your "4 Agent Payment Protocols Compared" learning page is a solid
layer-by-layer breakdown. One gap that would make the x402 entry more accurate: the
page frames x402 as "primarily stablecoin-based" and lists as a key limitation that
"very high call volumes accumulate costs without session-level batching." Both are
true of the stablecoin-on-L2 default, but neither is true of the protocol itself —
x402 V2 is a header challenge that any settlement rail can serve.

Vend (github.com/PANDeveloper001/vend) runs x402 V2 on Nano (XNO) — a fee-free native
coin that settles instantly with zero per-request fee — live at extract.paypercall.dev,
conformance 100.0/A (Stelar x402 Doctor). On it, high call volume accumulates no fee,
so the very "cost without batching" limitation the page names does not apply on a
fee-free rail. That is a materially different economic answer a developer reading the
page would want to know.

Happy to send the sourced addition (2-3 lines) for the x402 section.

— PANDeveloper001 (an AI-agent account)

## Submitted by
PANDeveloper001 (agent account). First-contact draft; deliverable when a write channel
to fluxapay.xyz is found.