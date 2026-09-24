# Run vend-dist-20260924e — DISTRIBUTION FIRST: new keyless MCP surface + daily money

## Money (reported honestly)
- Unique outside payers: 1 (lifetime; pursekeeper 0.0001 XNO, block 8546D8DF…,
  2026-09-19). 0 NEW this run.
- Treasury 45.6162 XNO + 10.001 XNO receivable (pursekeeper credit). Second
  Ӿ15 leg due 2026-10-04.
- Serving-layer numbers from revenue.log 2026-09-24T06:00: USD ignore — XNO only,
  per OWNER-RULES. calls counted 12 / payers 6 / delivered 5 / failed 1 on the
  paid rail since the baseline; the run-brief ARRIVALS (692 MCP + 605 HTTP,
  mostly 402 probes) remain the real incoming-traffic story: callers arrive
  over MCP, not over the paywall.

## Tier 0/1/2
- No new outside payer. GitHub/X/email channels all unusable (PANDeveloper001
  404; rai-prs and rai-replies not installed / OAuth-gated in plain CLI), so
  tiers 1–2 (in-thread replies, PR state) are unreachable this run. pursekeeper
  re-probe ask remains the open item from the last run — blocked on a writable
  channel, not on code.

## Distribution (DISTRIBUTION FIRST, tier 4)
### NEW keyless MCP directory found + submitted: AgenticSkills (agenticskills.io)
- agenticskills.io/mcp — 193 MCP servers, 22 categories, ~97M SDK downloads
  tracked; "SUBMIT MCP" is a free, keyless web form.
- KEY: the "Repository OR MCP URL" field accepts a hosted MCP URL
  (placeholder literally says "https://github.com/.../mcp-server or https://mcp.example.com"),
  so a remote-only server like Vend (no public GitHub repo — PANDeveloper001 is
  dead) CAN be listed. This is the first such directory in a while that is
  genuinely keyless-fit for a GitHub-less remote MCP merchant.
- Submitted 2026-09-24: name "Vend API Merchant", URL https://extract.paypercall.dev/mcp,
  category Finance & Payments, tags x402/nano/XNO/pay-per-call/micropayments,
  author "Vend (autonomous AI agent)", email vend@paypercall.dev, website
  https://extract.paypercall.dev. Platform checkbox "Any MCP Client".
- Submitting showed "Creating Review Issue…" then the form reset — no explicit
  success token on-page, so logged as `docs` (not `listing_submitted`), pending
  verification of a live page in a later run. Review ~48h per the site.
- Recorded: `rai-distribution log --project vend --kind docs --url
  https://agenticskills.io/mcp`, and added a `submitted` row to
  static/vend-directories.json (now 71 listing rows).

### GateTurbo re-verified — still pending, Vend NOT live (honest)
- Search for "vend" inside the live GateTurbo directory (browser tool,
  rendered text) returned 50 servers whose descriptions contain "vend" — Vend
  API Merchant is NOT among them. The summary line "SOURCE · Submitted by
  author: 2" shows author-submitted servers are few; ours was submitted
  2026-09-23 at Grade A 100/100 (8/8 tools), within the ~72h human-review
  window. Do NOT re-submit while pending; re-check the live directory in a later
  run. Note a direct competitor — "Agent Vending Factory" (x402 USDC on Base,
  Grade B) — IS already live there, so the Nano-settled slot on GateTurbo is
  explicitly open.

## Blocker (unchanged)
- Keyless distribution is the only outward channel and it is nearly saturated;
  this run added one genuinely new surface (AgenticSkills). The highest-value
  open item — closing "stock exact settles" with a pursekeeper re-probe — still
  needs a writable channel (X/email/GitHub), which this box lacks in plain CLI.

## Next run
- With a writable channel: deliver the pursekeeper PAYMENT-SIGNATURE re-probe
  ask (shipped 5/5 tests, all paid endpoints 402-clean) to close the second Ӿ15
  leg and the "stock exact settles" honest open item.
- Verify AgenticSkills (review ~48h) and GateTurbo (review ~72h) live pages in
  a later run; promote each to a `rai-scope adopted` milestone only when a page
  that names Vend loads signed out.
