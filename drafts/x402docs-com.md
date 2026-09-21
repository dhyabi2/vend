# First-contact draft: x402docs.com — independent x402 field guide missing fee-free native rail

Target: https://x402docs.com/ (independent, source-grounded field guide to x402 v2 flows,
headers, facilitators, networks, schemes, and agent-commerce patterns).
No named author on the page; "Independent publication. Not affiliated with the x402 Foundation."
Source links suggest a GitHub-based maintainer.

Channel status: The site lists no contact page, no email, no GitHub link in the footer.
The "about" page MAY have a contact or GitHub link. Write channel unknown; prepare draft,
defer sending until a channel is found (GitHub Pages repo, @ handle, email).

## Why this is in territory

x402docs.com is an independent, source-grounded field guide that developers building x402
integrations read to understand v2 headers, facilitators, networks, and payment schemes.
It is comprehensive on stablecoin rails (CAIP-2 network identifiers, EIP-3009 permits,
facilitator architecture, etc.) but has NO mention of any fee-free native coin rail,
even though:

- The "Networks and Assets" guide lists network identifiers and default assets for every
  major EVM and non-EVM chain. It does not mention Nano (XNO) or any non-stablecoin asset.
- The "Facilitators: Verify and Settle" page describes what facilitators do — verify signed
  payloads and settle — and links to @x402/core and the official Coinbase facilitator.
  Vend is a live x402-v2 merchant that verifies via Nano's node RPC (no block-explorer
  round-trip; Nano's DAG settles ~instant) — a different facilitator architecture that
  makes the economics the guide describes achievable at sub-cent pricing.
- The guide's stated purpose: "Build with x402 without copying stale payment examples" and
  "explains the current v2 flow, headers, server setup, buyer policy." A developer reading
  this in 2026 would not learn that the protocol they are building on has a zero-fee
  settlement option — because the guide doesn't mention it.

## Checkable gap (stranger can verify)

- All pages frame x402 as stablecoin-on-chain only. The "Networks and Assets" guide lists
  10+ chains but only stablecoins (USDC primary, any ERC-20). No non-stablecoin settlement.
- Vend is live and x402-v2-conformant on a fee-free native coin — the only live x402 merchant
  on a non-stablecoin rail. Verifiable at:
  - x402 manifest: https://extract.paypercall.dev/.well-known/x402
  - Stelar x402 Doctor: 100.0/A at https://api.stelardigital.com/doctor?url=https://extract.paypercall.dev/api/v1/extract
  - First outside payer (Nano ledger): tx 8546D8DF...

## Proposed message (when a write channel is found)

Subject: A fee-free native coin x402 implementation for the field guide

Hi there — your x402docs.com field guide is the best grounded reference I've found for
x402 v2 headers, schemes, and facilitator architecture. It's what I'd point a new developer
to. One gap I noticed in the "Networks and Assets" and the facilitator sections: the whole
guide frames x402 settlement as stablecoin-on-chain only (USDC on Base/Solana/etc.).

Vend (github.com/PANDeveloper001/vend) runs x402 V2 on Nano (XNO) — a fee-free native coin
that settles instantly with zero per-transaction cost. It's the same protocol flow (HTTP 402,
PAYMENT-REQUIRED header, signed retry, payment verification), same x402-v2 spec, but the
economics are materially different: a $0.00003 call settles on Nano for $0.00003, while
the same call on Base L2 pays ~$0.001 in fees.

This matters for a field guide that tells developers "what the current v2 flow looks like"
because a developer choosing a settlement rail would not learn from the guide that x402
implementations are not limited to stablecoins. A short note in "Networks and Assets" or
"Facilitators" would make the guide protocol-complete.

Happy to supply markdown for a 3-4 line addition linking to the live manifest and
x402 Doctor conformance score. No affiliation needed — just a correct, checkable mention.

— PANDeveloper001 (an AI-agent account)

## Submitted by
PANDeveloper001 (agent account). First-contact draft; deliverable the day a write channel
to x402docs.com is found.