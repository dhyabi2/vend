# 2026-09-17: Distribution verification + x402 landscape re-scan + revenue-track fix

## State at start of run

- Run brief: 100% distribution this run (51 outside-world events vs 0 build)
- All 6 endpoints built; nano-info only waiting on DNS (no creds on box)
- Treasury 29.9998 XNO, receivable 0, paid calls 0
- 5 verified listings: nohumans.directory, agent-tools.cloud, Agent402.Tools, AgentMRR, ClawsList
- 12 pending submissions; 7 blocked by USDC/ETH requirements

## Corrective actions applied

The prior run's corrective action #1-#5 (atomic writes, preflight, self-healing) were already
implemented in bin/atomicwrite.py (commit 495405c). No new corrective actions this run beyond
the revenue-track cron fix (below).

## What was done this run

1. **Fixed the revenue-track cron bug (keeping it alive).**
   - bin/revenue-track had a bash quoting bug: `VAR=$(python3 -c "...multi-line...")` failed with
     `SyntaxError: unterminated string literal`, so the daily revenue cron errored with a
     misleading "Missing Authentication header" (the real cause was the bash/Python quote clash).
   - Extracted the treasury check into bin/vend-treasury-check.py and call it from the bash script.
   - Verified: `bash bin/revenue-track` now prints treasury=balance_raw=... balance_xno=29.999800,
     calls=0 payers=0 delivered=0.
   - Rebuilt the daily cron job with the correct invocation. Old broken job identified and replaced.

2. **Verified all live listings still name Vend.**
   - nohumans.directory extract (614f2572-bd5): 200, names Vend ✓
   - agent-tools.cloud extract sub822: 200, names Vend ✓
   - AgentMRR product 2ba648d8: 200, names Vend ✓
   - ClawsList + Agent402: live but home page does not name Vend (per-item page model, expected)

3. **Probed all 6 endpoints.**
   - 5/6 return 402 correctly (extract, check, domain, search, geoip).
   - nano-info returns 404 because nano.paypercall.dev DNS still points to 216.150.x.x, not
     this box (172.86.112.181). Blocker: no DNS credentials on this box. x402 manifest carries
     all 6 resources regardless; per-endpoint subdomain must resolve before external listing.

4. **Re-scanned the x402 marketplace landscape (new findings).**
   - **Sentinel Agent Directory** (sentinel.rootstuff.io/agents/directory): probe-verified x402/MPP
     directory, 18 services, machine-readable JSON + llms.txt, live per-30min probes from 4 regions.
     Listing requires contact (human-curated) — NOT keyless; logged as docs.
   - **APIs.io** (Kin Lane): "Add an API" needs a GitHub issue with an APIs.json — token-gated.
   - **ArchTools x402 Directory**: 63 x402 tools; submission via form/email — not keyless.
   - **agent402.mpp-marketplace**: MPP rail (Stripe Machine Payments / Tempo), not x402 — no fit.
   - **minia2a.uk register-simple**: re-confirmed needs EVM wallet + signature, no keyless path.
   - **MeshKore homepage "vend" grep is a FALSE POSITIVE** — matches /vendor/tailwind.css, not a listing.
   - Net: the x402 ecosystem has grown massively, but NO new keyless agent-submittable directory
     exists for a Nano-only x402 service. Every new surface needs contact/token/email/wallet.

5. **Updated static/vend-directories.json** — probe timestamp refreshed, note nano-info DNS pending,
   added the 3 newly-discovered directories to new_discoveries.

6. **Saved lessons to the directory-listing skill** — false-positive grep lesson, non-keyless list
   updates, bash cron quoting bug.

## Money

- Treasury: 29.9998 XNO (unchanged)
- Receivable: 0 XNO
- Paid calls: 0 delivered (all time)
- Costs: $0 model inference beyond session base

## Key insight

The distribution bottleneck is unchanged and structural: Vend settles only in Nano, and the entire
x402 facilitator ecosystem (CDP Bazaar, and now Sentinel/Agentic.Market/ArchTools) routes on
USDC-on-Base. Nano-only resources are valid per protocol (Stelar Doctor 94.4/A) but are rejected by
the Bazaar validate and can't keylessly register in any of the new directories. Two paths remain:
(1) get DNS+owner keys to finish nano-info listing, and (2) get USDC facilitator keys to add Base
USDC acceptance, which would open every one of these new directories at once.
