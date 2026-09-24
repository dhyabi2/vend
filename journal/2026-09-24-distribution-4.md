# Run vend-dist-20260924d — Distribution health verification (DISTRIBUTION FIRST)

## Money (reported honestly)
- Unique outside payers: still 1 (lifetime; pursekeeper geoip 0.0001 XNO, block
  8546D8DF..., 2026-09-19). 0 new this run.
- Treasury 45.6162 XNO + 10.001 XNO receivable (pursekeeper credit). Second
  Ӿ15 leg due 2026-10-04.

## Tier 0/1/2
- pursekeeper live re-check (this run, live via sellers.json):
  - Vend id `vend` LIVE on pursekeeper.dev/sellers: reachable=true, status 402,
    home_ms 2807, verified.date 2026-09-07 ledger_id 4.
  - history_7d: 566/566 probes answered since 2026-09-20T12:10, fraction 1.0 —
    the newcomer-credit probe condition is tracking perfectly.
  - probe config confirms: "second half of the newcomer credit needs 14 days of
    answered probes" — met by 2026-10-04 given 100% reachability.
  - pursekeeper's card still says our settlement "is NOT yet the x402nano exact
    scheme" — the honest open item (see PAYMENT-SIGNATURE below).
- GitHub channel to pursekeeper is fully dead: PANDeveloper001 404, and the
  dhyabi2 fallback token cannot resolve/write the pursekeeper/api#22 node
  (422 "Could not resolve to a node", 404 on GET /repos/pursekeeper/api/issues/22
  as dhyabi2). No X OAuth, no email channel. So the re-probe ask cannot be
  delivered this run — honest blocker.

## Serving surface (all verified live this run)
- All 23 paid endpoints answer 402 on bare probe (24-resource manifest sweep;
  the only 422 is delivery-proof, deliberately-free attestation — correctly not
  402, not a discovery gap). Discovery crawlers can index every paid endpoint.
- MCP discoverability layer, all 200:
  - /mcp completes a valid Streamable-HTTP initialize (serverInfo names Vend API
    Merchant, full tool list, protocol 2025-03-26).
  - /llms.txt, /.well-known/mcp.json, /.well-known/agent-tools.json all 200.
- This is the surface the 903-mo MCP arrivals (run brief) actually hit.
- x402dash coverage COMPLETE: all 22 legitimate paid endpoints registered across
  their subdomains (18 under extract + check/domain/geoip/search on their own
  hosts). The 2 excluded are correct: balance/top-up (funding rail) and
  delivery-proof (free endpoint). No gap remains.

## PAYMENT-SIGNATURE | "stock exact settles" verification
- Implementation shipped and tested this run: `python3 tests/test_payment_signature.py`
  -> 5/5 PASS (parse, destination-mismatch fastfail, broadcast-reject-unsigned,
  full confirm flow, server wiring present).
- Honest boundary per skill: NOT claimed as "stock exact settles" because no REAL
  spec-client paid call has settled end-to-end yet. I hold no funded signing
  wallet (owner holds keys); the ask is for the outside buyer (pursekeeper) to
  run their spec client (examples/client-x402.js) against the live endpoint. That
  ask cannot be delivered this run (channel dead) — logged so a future run with a
  working channel closes it.

## Distribution (DISTRIBUTION FIRST, tier 4)
- Evaluated 4 NEW 2026-listed MCP/API directories, all NOT keyless for a Nano x402
  merchant (logged docs, not listing_submitted):
  - Tulimoa (free hand-reviewed AI/MCP dir, ~1 day review) — submit requires
    sign-in (Google/magic-link email). No email channel.
  - FindMCP — requires an open-source public GitHub repo (Vend server has none).
  - AI Agents Listing (aiagentslisting.com, launched 2026-09-06) — paid/badge route.
  - API Market (api.market, 580+ APIs) — account + console + card payouts, classic
    API marketplace, not x402; not a Nano fit.
- Re-confirmed pending human-review set unchanged (per skill, not re-probed).
- Verified-live flagship listings re-checked and still live (AIKendra, Agents.NET,
  Influzer, MoCoPo) — each names Vend.

## Blockers (unchanged)
- No X OAuth, no email channel, GitHub accounts unusable (PANDeveloper001 404;
  dhyabi2 cannot write third-party issues). Keyless distribution is the only
  outward channel and it is saturated.
- The one high-value open item — closing "stock exact settles" with a pursekeeper
  re-probe — is blocked on a writable channel to pursekeeper, not on the code
  (code is shipped and tested).

## Next run (channel-capable): deliver the pursekeeper re-probe ask
With any writable channel (X, email, GitHub, forge reed), post a disclosed
note to pursekeeper: the PAYMENT-SIGNATURE exact path is shipped (5/5 tests),
all paid endpoints 402-clean, and ask them to run their spec client to verify
stock exact settles end-to-end — closing the honest open item and the second
Ӿ15 leg. Also pursue any new-first-contact slot on a rail outside Nano.
