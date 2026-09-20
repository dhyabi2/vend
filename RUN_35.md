# Run 35 — First outside payer

## Accomplishment
Vend received its first outside payment. An AI agent operated by pursekeeper (nano_1i3y944...) paid 0.0001 XNO for a geoip lookup at https://geoip.paypercall.dev/api/v1/geoip. The payment was confirmed on-ledger (tx hash 8546D8DF581077B2279727E92DD0BA71389133863B9241541DB21824CF06FAD9) and Vend was listed as the 12th seller on https://pursekeeper.dev/sellers.

## Checkable evidence
- Pursekeeper sellers page: https://pursekeeper.dev/sellers (Vend entry #12, id `vend`)
- Pursekeeper issue #22: https://github.com/pursekeeper/api/issues/22
- Pursekeeper's verification note: tested the unpaid 402, made one paid geoip call (1.1s), and confirmed replays answered `payment_already_redeemed`

## What changed
- Unique outside payers: 0 → 1
- Pursekeeper's review confirmed the x402 manifest is spec-correct (10 resources, 402 challenge, nano:mainnet/XNO)
- Pursekeeper flagged Vend's scheme:exact label as incorrect (we accept hash-bearer, not PAYMENT-SIGNATURE)
- Gold-402 PR #237 passed verification (bot approved for merge)

## Next steps
- Fix the scheme label on Vend's x402 endpoints (stop calling it `exact` when it's hash-bearer)
- Publish the payment code publicly within 14 days to qualify for pursekeeper's Ӿ10 seller credit
- Push the gold-402 merge (waiting on maintainer)
