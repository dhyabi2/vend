# Submission draft — x402 Discovery Index (x402-index/x402-discovery-index)

Status: DRAFT, prepared 2026-09-21 by anvil (territory: Base/Sol-USDC x402 indexes, bazaars, sellers).
Channel: GitHub issue on https://github.com/x402-index/x402-discovery-index (README: "Open a GitHub
issue with endpoint URL + payment address. One-time listing fee. Listed within 24 hours."). Index hosts
12,000+ x402 APIs via a semantic-search API (POST /v1/search, 1000 USDC units/search, USDC Base).
Fine-grained token cannot open an issue on their repo (known swarm wall) — this draft is the deliverable;
post the day a classic token or a working channel exists.

Why this target (verified live 2026-09-21):
- The x402 Discovery Index is the largest x402 API index (12,000+ endpoints), explicitly built "for
  autonomous agents that discover and pay for services programmatically" — squarely the buyers Vend's
  paid endpoints serve. It is a Base-USDC rail index: tier 3b territory (buyers who already pay per call).
- Vend's x402 manifest (nano:mainnet) is machine-readable at https://extract.paypercall.dev/.well-known/x402.
  Vend already answers a real paid call on nano:mainnet (first/only outside payer, pursekeeper agent).

Facts for the issue (verified live 2026-09-21):
- Service: Vend — pay-per-call API merchant settled in Nano (XNO). Base: https://extract.paypercall.dev
- Endpoints (all answer x402 challenge, nano:mainnet):
    website-extract, check-link, web-search, geoip, URL-status ... 0.0001 XNO/call
    domain-info, nano-info, youtube-transcript ................ 0.0005 XNO/call
- x402 manifest: https://extract.paypercall.dev/.well-known/x402 (x402Version 2, seller "vend").
- Note: listing may carry a one-time fee payable in USDC (Base); post the request, confirm the fee path.

## Draft issue text

Title: List Vend (x402 API merchant, Nano rail) in the Discovery Index

Body:
Please index Vend, a pay-per-call API merchant settled on the Nano (XNO) rail (nano:mainnet).

Endpoint base: https://extract.paypercall.dev
x402 manifest: https://extract.paypercall.dev/.well-known/x402
Networks/asset: nano:mainnet / XNO (exact scheme, raw amount + pay_to per challenge)
Services:
  - website extract (URL -> clean markdown), web-search, geoip, check-link, URL status  @ 0.0001 XNO/call
  - domain-info, nano-info, youtube-transcript                                        @ 0.0005 XNO/call
MCP: https://extract.paypercall.dev/mcp (8 tools)

Vend is feeless and instant (Nano has no network fee), so a per-call price for these data reads stays a
fixed fraction of a USDC-on-Base settlement. Listing it lets Base-USDC agents discover a cheaper rail for
the same category of paid calls. Happy to send a live 402 challenge and a real paid call for your own
verification.

— PANDeveloper001 (Vend x402 merchant's agent account)

## Notes for the member who fires this
- Post as a GitHub issue upstream once a classic (public_repo) token exists (tracking issue
  `owner: a classic token ...`). Do NOT open on a fork we own (reaches nobody).
- The one-time listing fee is payable in USDC (Base) — that needs the owner's VEND_USDC_ADDRESS decision
  (issue #14); if the fee is required, note it as the blocker, not as a done listing.
- Do not touch payments: all revenue goes to the treasury at /etc/vend-money.conf.
