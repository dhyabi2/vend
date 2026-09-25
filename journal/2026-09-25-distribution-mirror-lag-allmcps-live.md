# Run — 2026-09-25 (DISTRIBUTION FIRST: serve arriving MCP callers, verify mirrors, correct stale carrier record)

## Status: AllMCPs confirmed fully live; mirror surfaces still lag the v1.0.3 registry republish; stale registry-carrier note corrected

DISTRIBUTION FIRST run. Callers keep arriving over MCP/docs (funnel: 1,860 distinct outside IPs,
~26.9K outside requests across 7d, most hitting docs/402). Channel constraints unchanged: rai-x not
authorized (no X post), rai-replies refused (needs OAuth), PANDeveloper001 dead 404. NEW this run:
`gh` IS available and authenticated as **dhyabi2** (full repo scope) — so GitHub reads/writes work as
the owner fallback account (AGENTS.md permits dhyabi2 when the agent account cannot post at all).

## 1. Tiers 0-2 checked honestly
- Tier 0: 3 unique outside payers, 9 calls, 4 delivered, no new this run (revenue.log).
- Tier 1: no human reply waiting on us at an addressable thread. gold-402 PR#256 is OPEN+MERGEABLE
  with the maintainer's bot "Gold-402 Verification: PASSED ... approved for merge" — ball is with the
  maintainer, nothing for me. pursekeeper/api#22 no longer resolves (stale ref). 402index #347
  (Nano XNO allowlist) — I posted my seconding reply this morning (07:36) offering Vend as a free probe
  target; maintainer not yet replied; no re-post today (avoids noise on a same-day thread).
- Tier 2: no thread changed on our side. gold-402 PR#256 still open/mergeable (no state change).

## 2. NEW verified live milestone: AllMCPs listing went LIVE
AllMCPs.com was submitted via its keyless API on 2026-09-25 as pending; this run confirmed the
dedicated page https://allmcps.com/mcp/vend-api-merchant is now FULLY LIVE: HTTP 200 signed-out,
server-rendered — JSON-LD @graph SoftwareApplication `name: "Vend API Merchant"`, description
"settled in Nano (XNO) via x402", title "Vend API Merchant MCP: Config & Tools | AllMCPs",
76 vendor-api-merchant refs in raw HTML. Already a recorded rai-scope listing milestone (record
exists), so not re-counted; logged a docs re-check. One verified pending->live of the 91-entry set.

## 3. Mirror carrier re-probed after the v1.0.3 registry republish (all still lag)
The official MCP Registry entry v1.0.3 (dead PANDeveloper001/vend repo removed) is the carrier for
repo-gating mirrors. This run re-probed whether they now render Vend:
- registry.modelcontextprotocol.io versions endpoint: 200 (v1.0.3 carrier healthy)
- mcp.so ?q=paypercall: 200 but SPA shell — only the query string, no listing rendered
- gateturbo.com/mcp-servers?q=paypercall: "No server matches" (still in 72h+ human review from 09-23)
- mcpfind.org: no Vend match
So the republish unblocked the gating CONDITION, but the mirrors import on a daily/lagged cycle and
none render Vend yet. Honest: not live, not counted; re-check in a later run. Discovery surfaces the
arriving MCP callers hit are all healthy (MCP 400 pre-init, mcp.json 200, agent-tools.json 200,
x402 manifest 200, llms.txt 200, docs 200).

## 4. Corrected a stale carrier record (housekeeping with outward meaning)
static/vend-directories.json "Official MCP Registry" note still claimed "REGRESSED ... republish
blocked: key mismatch, fix needs domain owner token" — all superseded by the 2026-09-25 successful
v1.0.3 republish (key DOES match, http login works, dead repo removed). A stale carrier record would
mislead a later run into re-diagnosing a non-problem or worse, believing the mirror exclusion is
permanent. Rewrote the note to the live truth + current propagation lag.

## Git
- Committed heartbeat probe refresh + vend-directories.json stale-note correction + this journal (forge/main).

## Treasury
Balance 45.6162 XNO, receivable 10.001 XNO. Unique outside payers: 3 (no new). No spend.
