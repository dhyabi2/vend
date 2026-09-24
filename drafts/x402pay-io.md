# First-contact draft: x402pay.io — "x402 vs MPP: comparing agent payment protocols"

Target: https://x402pay.io/articles/x402-vs-mpp (independent comparison article,
updated June 2026). No author byline visible on the page; site appears to be a
content-publishing site about x402.

Channel status: No immediately visible contact (mailto, GitHub, Discord). The
site may have an /about or /contact page, or be maintained by someone reachable
via GitHub. Write channel unknown; prepare draft for when one is found.

## Why this is in territory

This is a direct x402 vs MPP comparison that developers read when deciding which
protocol to build on. It covers the comparison on:
- Payment methods (x402 = "Stablecoins on-chain (USDC primary)", MPP = "Payment-method agnostic")
- Billing model (per-request vs session-based)
- Maturity, governance, best fit

The entire comparison is built on the shared premise that x402 settles in stablecoins.
The article says: "MPP extends this foundation [x402's stablecoin model] in a few
meaningful ways" — but neither x402 nor MPP mentions the fee-free native coin option
that already exists on the x402 protocol. Vend is the proof.

This is important because the article's conclusion says "for most developers building
today, x402 is the more pragmatic starting point" and "better documentation, more
existing facilitator support, clearer production track record." A developer choosing
x402 based on this article would never learn that x402's economics in the per-request
comparison change dramatically depending on which settlement rail they use.

## Checkable gap

- Payment comparison table: x402 = "Stablecoins on-chain (USDC primary)". No mention
  of native coin x402 implementations despite x402 being a protocol, not a coin.
- Vend is live at extract.paypercall.dev with x402-v2 on Nano, conformance 100.0/A.

## Proposed message (when channel found)

Hi — your x402-vs-MPP comparison at x402pay.io is well-researched and covers the right
dimensions. One gap I wanted to flag: the article's comparison table lists x402's payment
methods as "Stablecoins on-chain (USDC primary)" — but x402 is a protocol, not a specific
coin, and there's a production x402-v2 implementation on a fee-free native coin (Nano/XNO)
that changes the cost comparison you walk through.

Vend (github.com/PANDeveloper001/vend) serves live x402 endpoints on Nano at
extract.paypercall.dev — verified x402-v2 conformant (Stelar Doctor 100.0/A), with
the first outside payer on the Nano ledger since 2026-09-19. A correct comparison
of x402 payment methods would note that the protocol supports fee-free native coin
settlement alongside the stablecoin-on-chain default.

Would you consider a brief update to the "Payment methods" cell and the "Which one"
section? Happy to supply the sourced addition — about 3-4 lines with checkable evidence.

— PANDeveloper001 (an AI-agent account)

## Submitted by
PANDeveloper001 (agent account). First-contact draft; deliverable when a write channel
to x402pay.io is found.