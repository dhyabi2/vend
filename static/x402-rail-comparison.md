# x402 settlement rails, measured: Nano vs Base USDC

A plain comparison for anyone building an agent that pays per call. Same protocol
(x402 v2), two settlement rails. Numbers below are what we could measure today,
not projections — each is cited to a public source or to a payment we actually
served.

## Why this matters

x402 is the HTTP-402 payment standard for AI agents: you call an endpoint, it
answers 402 with a payment request, you pay on a ledger, retry, get the data.
The rail the money settles on is the part agents don't usually compare. Today
that rail is overwhelmingly one chain.

## What the public directory data says

x402 List, which measures x402 services directly, reported on 2026-09-05
(https://x402-list.com/state-of-x402):

- 659 x402 services listed; 592 "payment-ready"; only **13 delivery-verified**
  (someone actually paid and received the product).
- Of 659 services, the overwhelming majority settle on **Base USDC**
  (598 of 659 per the ecosystem breakdown / ~95%).
- Median asking price: **$0.01 per call**.
- On-chain USDC settlement volume measured across facilitators: $1.22M / 30 days.

Base being dominant is not a judgement — it is where the incumbent tooling
(Coinbase CDP Bazaar, most facilitators) has settled. It is also why Nano is
interesting: the median asks ten cents-per-hundred calls, and most of that is
settlement overhead, not data.

## Per-call price, sticker

Price of XNO at writing: $0.339 (CoinGecko). What Vend actually charges and served:

| Endpoint | Charge (XNO) | ≈ USD | Served (verified) |
|----------|--------------|-------|-------------------|
| extract / check-link / web-search / geoip | 0.0001 | **$0.000034** | geoip: yes, 2026-09-19 |
| domain-info / nano-info | 0.0005 | $0.00017 | — |

Against the $0.01 median on Base USDC, Vend's per-call ask is roughly
**1/290th** of the median USDC sticker price for the cheapest endpoints.

Do not read that as "Nano data is 290x better." It is a statement about the
price of settlement and per-call metering, which is where the two rails differ
most. Base USDC min gas rounds a $0.002 call up; a feeless chain does not.

## Where the cost actually goes

On Base USDC, the per-call economics are dominated by:
1. The facilitator's settled-payment mechanics (a signed off-chain authorization
   plus settlement, amortised across uses).
2. Gas on settlement. Base L2 gas is cheap compared to L1 but not zero, and for
   a $0.002-0.01 ask, the fixed costs are a real fraction.
3. The directory/listing economics: several x402 directories charge USDC to list
   or verify (e.g. a $0.10 USDC programmatic submission, a $0.99 wallet-connect
   directory fee, 1000-sat listing fees), so sellers price those in.

On Nano (XNO):
- **Transaction fee: 0.** A send block settles for free.
- **Finality: ~1 second.**
- No "gas" denominated in a second asset; the fee is not a hidden cost line.
- Nano has been live since 2015 with no issuer that can freeze or reverse a
  settlement — there is no account that can blacklist a payer or a seller.

The trade-off, honestly:
- Nano wallet/library support is far smaller than EVM. Your agent needs a Nano
  wallet or an x402 client that speaks nano:mainnet. Most off-the-shelf x402
  clients are USDC-first.
- Fewer directories accept a Nano-only endpoint; several big ones (CDP Bazaar,
  x402scan, 402index, Satring) list only EVM rails today. So a Nano-only seller
  is discoverable on fewer surfaces.
- Nano is not EVM: an endpoint that wants to also accept USDC must add a second
  rail on the same 402 (an EVM address + a USDC accept), which is work.

## Reality check: what settles

The most sobering number above is **13 delivery-verified** out of 659. Machine
payments mostly are NOT happening yet — directories list, agents talk, and few
money moves. The first real Nano payout we confirmed was a single 0.0001 XNO
geoip call (block 8546D8DF581077B2279727E92DD0BA71389133863B9241541DB21824CF06FAD9)
to an agent account on pursekeeper.dev — a live machine-to-machine x402 payment
on nano:mainnet, delivered in ~1.1s. It is small because the first payer is
always small. The point is the rail held for a real autonomous payment, at a
per-call cost that is effectively free to move.

## Bottom line

- If your agent pays USDC today and it works: switching to Nano only makes sense
  if per-call cost or no-counterparty matters to you. It can, and then Nano's
  ask is ~1/290th of the median with no tx fee.
- If you are building machine-payment infrastructure and do not yet support
  nano:mainnet, that is the largest price gap left in the x402 ecosystem.
- Nano's limits are real: smaller tooling, fewer directories, no EVM interop
  out of the box. Any honest comparison has to say so.

Sources: x402 List state page (2026-09-05), CoinGecko (XNO price), Nano protocol
(finality/fee), Vend's own served-payer journal (block 8546D8DF…). Prices of
XNO move; treat USD conversions as "at writing, $0.339".
