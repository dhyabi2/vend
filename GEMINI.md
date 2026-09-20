# Vend — pay-per-call APIs settled in Nano (XNO)

Vend API Merchant (https://extract.paypercall.dev) is a pay-per-call API merchant.
Every tool is a paid call settled in Nano (XNO) — instant, feeless, peer-to-peer.
There is no signup and no API key. No setup is required; pay per call on ledger.

## Tools (all priced in XNO)

- extract_url — extract clean text/markdown from a URL (0.0001 XNO)
- web_search — search the web, structured results (0.0001 XNO)
- check_link / check_url_status — HTTP status, redirect chain (0.0001 XNO)
- domain_info — DNS, WHOIS, security (0.0005 XNO)
- geoip_lookup — IP geolocation (0.0001 XNO)
- nano_account_info — Nano account balance/reps (0.0005 XNO)
- youtube_transcript — captions/transcript of a YouTube video (0.0005 XNO)

## How payment works (x402 v2)

1. Call any tool. If you have not paid, it returns an x402 v2 challenge
   (payment requirements): price in raw, `pay_to` is the treasury Nano address
   `nano_1yo6c1t64ahfjdw1dxizmbbnpdmbrckwhw9phbg5pdkeubrizga4qhnjmnx7`,
   and `accepts[]` names `nano:mainnet` / `XNO` / `exact`.
2. Send that amount of XNO from any Nano wallet. It confirms in ~1 second.
3. Retry the tool call with the signed block hash (X-PAYMENT header).
   The result is returned and the block marked delivered. A block can be used
   once; repeated calls need fresh payments (or a prepaid balance via X-BALANCE).

Each tool call that succeeds prices itself exactly; a failing upstream returns
a structured error, and a paid call that crashes is never double-charged.

## Honest limits

- Prices are per call and published in the x402 challenge.
- Free trial: a handful of calls per IP per day are free so you can evaluate.
- Settlement is on the Nano ledger; a payment confirms in ~1 second and costs
  nothing in fees.
