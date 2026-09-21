# Run (anvil) — 2026-09-21: USDC blocker verified across full territory; nohumans.directory now a 2nd fully-live Nano listing; agent402.tools re-verified

## Money (reported honestly)
- No new unique outside payer this run. Tier 0 remains 1 (lifetime; pursekeeper geoip, 2026-09-19).
- No new on-chain settlement this run. (Treasury figures live in /etc/vend-money.conf, owner-guarded.)

## Tier 0/1/2
- Tier 1: no outside reply waiting (checked vend-bridge waiting — all 15 anvil conversations are USDC-gated
  directories, none answered; the pursekeeper thread is outside my territory).
- Tier 2: no anvil thread changed state (no rai-replies auth; checked the 3 leads + recorded contacts).

## Adoption / territory work (the 40%)
### Confirmed the VEND_USDC_ADDRESS block is total across anvil territory (owner decision #14)
Probed x402 surface after surface this run; EVERY corpus/USDC directory rejects Vend's nano:mainnet-only 402:
- Circle-Discovery-API (1143 resources, EVM/Solana USDC) — no Nano
- Ampersend-Marketplace (Base/Sol USDC x402 catalog) — no Nano
- x402hub (6,209 services, CDP Bazaar clone) — no Nano
- 402index.io (try: verified the register rejects with `assetKnown:false` for XNO; not in their asset list)
- x402-list.com, x402scan.com (SIWX wallet auth), pay.sh (Solana Foundation, USDC), Agentic.Market (USDC),
  x402.be, x402 Endpoint (endpoint.x402jp.com)
Documented all 8 as `blocked` in static/vend-directories.json (PR #38) so no run re-derives them.

### Two NEW surfaces discovered (exceeded floor of 5 via claimed leads + new discovery)
- x402.be — independent x402 dashboard (5,925 servers, aggregates CDP+PayAI Bazaar). Vendor absent. USDC-gated.
- x402 Endpoint (endpoint.x402jp.com) — cross-directory catalog (17,089 endpoints, PR-driven
  github.com/kato9292929/endpoint). Vendor absent; aggregates USDC-settled accepts only.
Claimed the 3 knurl leads for my territory (Circle-Discovery-API, Ampersend-Marketplace, x402hub).

### The two REAL Nano-live listings in anvil territory (both re-verified this run)
1. **agent402.tools** — re-verified live across all 5 Vend subdomains (extract/domain/geoip/check/search),
   pages 35-36 of /api/index, health=1, routable=true, networks=[nano:mainnet], source=manifest via
   /.well-known/x402. This is the flagship Nano x402 index for anvil.
2. **nohumans.directory** — ALL 5 Vend endpoints now VERIFIED (chain: nano): extract(614f2572-bd5),
   geoip(2a406239-a41), check-link(d7c5f05d-332), domain-info(f11a7489-f87), web-search(71b91915-047).
   Cleaned up a stale duplicate search listing — the manifest path is /api/v1/web-search, NOT /v1/search
   (a wrong path 404s and stalls as unverified).

## Improvements (tier 5)
- Updated vend skill anvil-territory section: corrected "single exception" → the two true Nano indexes
  (agent402.tools + nohumans.directory), documented the nohumans status-probe trick (re-POST → returns live
  status) and the endpoint_url immutability trap.
- swarm/vend#37: escalated VEND_USDC_ADDRESS as THE single unblocking lever for the whole anvil territory.
- swarm/vend#38 (PR): 8 USDC-gated surfaces documented as blocked.

## Blockers (unchanged, owner-owned)
- VEND_USDC_ADDRESS unset — blocks every USDC-denominated directory AND any first-contact conversation that
  could put Nano in front of existing USDC buyer flows. The #1 lever for the whole territory.
- No working first-contact channel this run: email unconfigured, GitHub fine-grained token can't PR/issue on
  third-party repos, no wallet to pay satring's listing fee. Forcing a first contact to a USDC-gated directory
  to list a Nano endpoint their validator rejects would be a false listing, so I documented+escalated instead.
- Feature: PAYMENT-SIGNATURE acceptance (parses X-PAYMENT payload.block) not shipped — the #1 conversion lever
  once the USDC accept lands.
