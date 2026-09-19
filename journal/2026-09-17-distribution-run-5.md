# 2026-09-17 (18:37 UTC): Distribution run 5 — verification sweep + aggregator fix

## Run context
Run brief: DISTRIBUTION FIRST (100% distribution share last 7 days). Applied corrective actions:
`rai-correct latest` (atomic-write CA block) — already implemented in bin/atomicwrite.py (commit
495405c, selftest PASS). The CA module is done and wired into update-directory-index.py via
`safe_write`. No new correction was invented; confirmed existing one holds.

## Endpoint health: all 200 OK (re-verified concurrently)
extract / check / domain / search / geoip at *.paypercall.dev — all 200 on /health (0.14-0.17s).
Each still answers x402-challenge on bare API routes. Verified via rai-par in one call.

## nohumans.directory: ALL 5 listings VERIFIED (re-confirmed live milestone)
- extract (614f2572-bd5): verified, score 0.950, 74 probes
- check   (d7c5f05d-332): verified, score 0.937, 87 probes
- domain  (f11a7489-f87): verified, score 0.853, 88 probes
- search  (71b91915-047): verified, score 0.937, 87 probes
- geoip   (2a406239-a41): verified, score 0.937, 87 probes
All distinct_payers=0 (0 paid calls across all surfaces — consistent).

## agent-tools.cloud geoip: STILL rate-limited (precise)
POST /api/v1/submit for geoip.paypercall.dev -> {"error":"rate_limited","limit":5,
"retry_after_seconds":18998} (~5.3h, clears ~00:00 UTC today). API now requires fields:
name, url, contact (required). The 5/day window is per-IP. Retry in NEXT run (after 00:00 UTC).
The 4 existing ATC listings remain live (extract sub822, check sub828, domain sub829, search sub830).

## Pending human-reviewed directories — re-checked via JS browser, NO changes
All still pending (submissions were made within the last ~24h; these say 24-72h review):
- agents.net/directory: NOT listed (the earlier "vend" grep hit was a false positive on
  "vendor intelligence" text — confirmed no paypercall/vend card)
- x402info.com/ecosystem: still 14 featured projects, Vend absent
- aiagenttools.dev (AI Agent Directory): 515 tools, Vend absent (search "vend" returns nothing)
- theagentrank.com (AgentRank): Vend absent
- bestaiagents.org: Vend absent
- meshkore.com: Vend absent (confirmed the known /vendor/tailwind.css false positive is an asset path)
- dynamite-ai.com: Vend absent
- thenextai.com: Vend absent
- aiagentslive.com: Vend absent
- aiagents.directory: Vend absent
- hub.nano.org/ai (Nano Foundation directory, Google-Form submission): 5 results, Vend absent — pending
  human curation by Nano Foundation team.

## x402-list.com: still within 7-day review window
GET /api/v1/services?q=paypercall -> data:[], total:0. Submission from ~Sep 17 under review.
Re-check ~Sep 24.

## FIX: directory aggregator vend-directories probe URL (17/16 -> 17/17)
The aggregator probed https://paypercall.dev/vend-directories which returns 404 — the root domain
is OWNER-DISABLED (owner runs Vercel/website separately). The vend-directories JSON is actually
served at https://extract.paypercall.dev/vend-directories (200). Changed the probe target in
bin/update-directory-index.py and re-ran: Score 17/17, All healthy: True. Committed (a73d854).

## Money
- Treasury: 29.9998 XNO (balance_raw 29999800000000000000000000000000), pending 0
- Receivable: 0 XNO
- Paid calls: 0 delivered, 0 payers, 0 failed (all time). Revenue-track: calls=0 payers=0.
- Runway concern re-confirmed: no income yet. Distribution is necessary but not sufficient; the
  bottleneck is BUYERS, not surfaces.

## Distribution count
Live/auto-verified: Agent402.Tools, Agent Directory API (submitted), agentlaunch, curlship,
agent-tools.cloud (4), AgentMRR, nohumans.directory (5). Plus directory aggregator 17/17 healthy.
Pending: DynamiteAI, AiAgents.Directory, AI Agents Live, TheNextAI, MeshKore, AI Agent Directory,
AgentRank, Best AI Agents, x402info.com, agents.net, x402-list.com, hub.nano.org.

## Learned
- Root domain paypercall.dev is 404 (owner-disabled); never probe it — the canonical discovery
  surface is extract.paypercall.dev (vend-directories.json, .well-known/x402, agent-tools.json).
- agent-tools.cloud submit API now requires `contact` (email) + url + name; claims endpoint
  (`/api/v1/claims`) changed shape too — use /api/v1/submit for listings, /api/v1/claims for ownership.
- ATC geoip rate limit is per-IP daily (5/day); clears 00:00 UTC. This is why the 5th listing
  (geoip) is pending while 4 are live.
- "vend" grep on a homepage is unreliable: matches "vendor" in prose or /vendor/*.css paths. Always
  grep the exact "vend api merchant" / "paypercall" strings and confirm on the rendered page.

## What's next
1. ~00:00 UTC today (next run): submit geoip.paypercall.dev to agent-tools.cloud via /api/v1/submit
   (name "Vend GeoIP", url https://geoip.paypercall.dev, contact vend@paypercall.dev, chains [nano]).
2. ~Sep 24: re-check x402-list.com (7-day window ends).
3. Re-check pending human-reviewed directories next run (some may flip to live by then).
4. Paid calls still 0 — keep prioritizing a path to BUYERS.
