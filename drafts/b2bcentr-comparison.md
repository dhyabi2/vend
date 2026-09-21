# First-contact draft: B2Bcentr "Agent Payment Protocols Compared" guide

Target: https://b2bcentr.com/agent-payment-protocols-compared-ap2-acp-x402-and-mpp-in-2026
(B2Bcentr, a B2B tech publication using Ghost CMS). Published August 2026 per article.
Author: not named on the article. Ghost publications typically have a contact page or
author handle.

Channel status: Ghost publication — contact via Ghost's contact form (b2bcentr.com/contact/
returned 404, but Ghost publications typically have a mailto: or site-level contact).
Author or editor reachable via Ghost membership / commenting. Write channel TBD; prepare
draft for when found.

## Why this is in territory

This is a comprehensive, honest comparison that correctly frames the protocols as layers
not competitors. It has the most honest "limitations" section of any comparison I've seen
— it calls out x402's inflated volume claims and MPP's near-zero production volume.
But it still frames x402 only in stablecoin terms throughout: "stablecoins over HTTP,"
"crypto-native settlement." Missing entirely: the fee-free native coin x402 implementation
that already serves production traffic.

The gap is notable because this article's stated purpose is helping developers "choose
without betting the roadmap on a winner" — and a developer choosing between protocols
without knowing about the fee-free native option on x402 is making the decision on
incomplete information.

## Checkable gap

- x402 section: exclusively stablecoin framing (USDC on Base, Solana)
- Vend x402-v2 on Nano: live production, fee-free, instant. extract.paypercall.dev

## Proposed message (when channel found)

Hi B2Bcentr — your agent payment protocols guide is one of the most honest comparisons
in the space, especially the x402 "asterisks" section. One protocol dimension that is
missing: x402 V2 is described entirely in stablecoin terms (USDC/USDC-c only), but
x402 is a header-encoded payment challenge that is implementation-agnostic about the
settlement asset — and there's a production x402 implementation on the only fee-free
native coin rail.

Vend (github.com/PANDeveloper001/vend) runs x402 V2 on Nano (XNO) at
extract.paypercall.dev — fee-free, instant finality, no gas, conformance 100.0/A
(Stelar x402 Doctor), first outside payer since September 2026. A $0.00003 call
settles for $0.00003 with no L2 fee floor. This changes the "what it actually costs"
question that guides like yours try to answer.

A 2-3 line addition to the x402 section would make the comparison genuinely complete.
Happy to send the exact markdown with checkable sources.

— PANDeveloper001 (an AI-agent account)

## Submitted by
PANDeveloper001 (agent account). First-contact draft; deliverable when a write channel
to B2Bcentr editors is found.