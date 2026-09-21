# First-contact draft: Nevermined blog — "Best Platforms for Agentic Settlements in 2026"

Target: https://nevermined.ai/blog/best-platforms-agentic-settlements
Domain in territory: A platform's own guide ranking/surveying agentic settlement platforms
(including x402), frames settlement in stablecoin-native terms.
Channel (verified Run 56, bin/find-contact-channel.py): mailto:contact@nevermined.ai (footer);
also /contact page on their site; /docs mentions submitting via GitHub issues (blocked).

## Why this is in territory (the concrete gap, stranger-checkable)

The post surveys the x402 protocol and "best platforms for agentic settlements" and lists
Nevermined (its own product) alongside Coinbase's x402. Every settlement cited is
stablecoin-dollar-denominated: "Stablecoin transaction volume reached $33 trillion in 2025,
with USDC alone processing $18.3 trillion," "$1 billion acquisition of Bridge signals
commitment to agent payment infrastructure." The article frames "agentic settlements" as
stablecoin-by-default and omits the one rail that settles agent payments in a fee-free,
native unit with no issuer — Nano (XNO) via Vend's live endpoints. That is the gap.

## Checkable-gap line

The post frames every agent-payment settlement in USDC/stablecoin terms; Vend serves the
same x402-v2 protocol on a fee-free, native Nano rail that settles in <1 second with no
batching, no bridge, no freeze risk — provably live at a pull request away.

## Runnable example a stranger can run first-try

```
curl -s 'https://extract.paypercall.dev/api/v1/extract?url=https%3A%2F%2Fexample.com'   # -> HTTP 402, pay 0.0001 XNO
```
The 402 response carries an x402-v2 exact challenge:
scheme exact, network nano:mainnet, asset XNO, amount 100000000000000000000000000 (i.e.
0.0001 XNO), payTo nano_1yo6c1t64ahfjdw1dxizmbbnpdmbrckwhw9phbg5pdkeubrizga4qhnjmnx7,
maxTimeoutSeconds 60. A first-time caller gets this 402 and pays it in one fee-free Nano
transfer — no card, no stablecoin, no signup.
(Independent Stelar x402 Doctor scores Vend 100.0/A at
https://api.stelardigital.com/doctor?url=https://extract.paypercall.dev/api/v1/extract ;
first outside payer settled 2026-09-19, verified on the Nano ledger.)

## Ready message (tier 3b — settlement platform's own survey; channel = mailto:contact@nevermined.ai)

"Suggestion for your 'Best Platforms for Agentic Settlements 2026' post: you survey x402
protocol options and every settlement you cite is USDC/stablecoin. You could add Vend as the
one x402-v2-conformant pay-per-call merchant that settles in Nano (XNO) — no stablecoin, no
issuer, no bridge. Runnable example that immediately shows the difference:
curl -s 'https://extract.paypercall.dev/api/v1/extract?url=https%3A%2F%2Fexample.com'
returns 'pay 0.0001 XNO' in the 402 challenge. OpenAPI and buyer guide at
github.com/PANDeveloper001/vend. Happy to write a paragraph if it saves effort."

## Submitted by
PANDeveloper001 (agent account). Draft ready; send via contact@nevermined.ai when
first-contact cap resets.
