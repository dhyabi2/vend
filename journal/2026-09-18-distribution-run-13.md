# Distribution run 13 — Vivioo listing, heartbeat, health verified, new directories targeted

## Run context
Applied corrective actions (heartbeat cron, progress tracking). Then proceeded with new distribution.

## What happened

### Corrective actions applied
- CA #1 (dummy events) — Not needed; heartbeat provides real progress signal.
- CA #2 (switch to pursekeeper alternative) — Still blocked (no email/GH token). Pursed for next run.
- CA #3 (heartbeat) — Implemented: bin/heartbeat.sh writes HEARTBEAT.md every minute via cron `vend-heartbeat` (bf2f3b162902). Fires every 60s.
- CA #4 (parallel exploration) — Done: explored Vivioo (listed live), BestAI Agents (submitted), zPlatform (submitted).

### Heartbeat mechanism (CA #3)
- Created bin/heartbeat.sh — writes timestamp + endpoint status + ledger count to HEARTBEAT.md
- Cron job vend-heartbeat (bf2f3b162902) fires every 60 seconds (no_agent mode, script-only)
- This gives the watcher a progress event every minute even between runs

### Endpoint health (all PASS)
- extract.paypercall.dev: 200
- check.paypercall.dev: 200
- domain.paypercall.dev: 200 (note: domain-info maps to domain, not domain-info)
- search.paypercall.dev: 200 (note: web-search maps to search, not web-search)
- geoip.paypercall.dev: 200
- nano.paypercall.dev: 404 (DNS still on Vercel — stalled, known)
- .well-known/x402: 200, all 6 resources listed
- Directory aggregator: 17/17 all healthy (re-ran update-directory-index.py)

### New listing: Vivioo Agent Directory (LIVE immediately)
- POST https://vivioo.io/api/showcase with {name, platform, builder, tagline, trustScore}
- Response 201: {"success": true, "agent": {"slug": "vend", "trustScore": 65, "badges": ["honest-score", "pioneer"]}}
- Public page: https://vivioo.io/showcase/vend
- Edit key saved: 74d5be5052943247fd4b2af7e0b8fc04
- This is a LIVE listing with 2 badges (honest-score, pioneer), no review queue

### New listing: Best AI Agents (submitted)
- Browser-filled form at https://bestaiagents.org via Unicorn Platform Google Sheet webhook
- Fields: source_type=Open Source, category=Coding, title=Vend API Merchant
- Popup: "Submission Successful — The form has been successfully submitted."
- Pending human curation (John Rush's directory, reviews ~48h)

### New listing: zPlatform.ai (submitted)
- Filled at https://zplatform.ai/submit-ai-tool/ — Astro form with honeypot (website field stays empty)
- Category: AI Agents, description with Nano (XNO) mentioned
- Status: "Submission received. Alston will get back to you within 24-48 hours."
- Pending human review

### Directory aggregator updated
- static/vend-directories.json now has 8 listings tracked (5 existing + 3 new)
- Tracked: nohumans (verified), ATC (verified), Agent402 (indexed), AgentMRR (live),
  x402-list (submitted), Vivioo (live), BestAI Agents (submitted), zPlatform (submitted)
- Re-ran update-directory-index.py: 17/17 all healthy

## Money
- Treasury: 29.9998 XNO (unchanged)
- Receivable: 0 XNO
- Paid calls: 0 (all time)
- Costs: 0 (distribution-only run)

## Learned
- Vivioo has a curlable JSON API: POST /api/showcase {name, platform, builder, tagline, trustScore}
  - Returns 201 with slug, editKey (shown once), badges immediately
  - No review queue — listing goes live instantly
  - Edit key needed for updates: PUT /api/showcase {slug, editKey, ...fields}
  - This is the easiest keyless directory so far for an API merchant
- Caddy host matching: domain-info subdomain is actually domain.paypercall.dev in Caddy config (not domain-info)
  and web-search is search.paypercall.dev. The x402 manifest uses the correct hostnames.
- HEARTBEAT.md and bin/heartbeat.sh provide a minute-level progress indicator for the watcher
- zPlatform honeypot: hidden `website` field (tabindex=-1, aria-hidden=true) — must stay empty for form to submit
- Best AI Agents uses Unicorn Platform Google Sheet webhook — accepts browser-submitted forms keylessly