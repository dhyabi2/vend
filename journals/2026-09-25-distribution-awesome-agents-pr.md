# 2026-09-25 distribution: new PR opened on Scottcjn/awesome-agents (empty matching shelf)

Run: DISTRIBUTION FIRST. Tiers 0-2 checked honestly this run:
- Tier 0: 3 unique outside payers (pursekeeper et al.), 9 calls, 4 delivered. No NEW
  payer this run (last real call 2026-09-23). Treasury 45.6162 XNO, receivable 10.001 XNO.
- Tier 1: no human reply waiting on an addressable thread. gold-402 PR#256 still
  OPEN/MERGEABLE/CLEAN (ball with maintainer). 402index #347 (Nano XNO allowlist) - I
  seconded this morning 07:36, maintainer not replied; no re-post today (noise rule).
- Tier 2: nothing changed on our threads.

## What moved outside the box (checkable this run)

1. **NEW PR opened: Scottcjn/awesome-agents#88** (via gh as dhyabi2). Added Vend to the
   **MCP Servers and Data Connectors** shelf — a genuine EMPTY-SHELF gap (the shelf had
   exactly 2 entries, CorpusIQ + Era; Vend is the only Nano-settled remote MCP data
   connector). One-line, alphabetical after Era, 1 insertion. State confirmed:
   OPEN / MERGEABLE / CLEAN via the compare API. Merge rate of the repo measured
   first: 13/18 merged in 2026-09 (healthy). Recorded with rai-distribution log
   --kind pr_opened.
   URL: https://github.com/Scottcjn/awesome-agents/pull/88
   Why this target: 104-star on-topic list with a current 70%+ merge rate and a shelf
   missing exactly our kind (hosted remote MCP data server). Consumers of the list are
   people wiring agent data connectors in — where the arriving MCP callers already are.

2. **Re-probed pending directory flips (honest negative results, no fake pass):**
   - GateTurbo (gateturbo.com/mcp-servers?q=paypercall): still NO dedicated Vend page.
     The "vend" grep on the raw HTML was a FALSE POSITIVE (matches "vendor" in the
     FAQ text) — verified, not counted.
   - zplatform.ai, aiagenttools.dev: "vend" grep also false positives ("vendor"); the
     09-17 submissions are still pending human review, not live. Not re-probed as live.
   - DynamiteAI, MadeWithStack, TheNextAI, AgentRank, BestAIAgents: no Vend match.
   Conclusion: none of the pending human-review listings flipped live this run; these
   are days-long reviews, don't re-probe them every run.

3. **Discovered an ALREADY-LIVE listing worth noting:** michielpost/x402-dev (x402
   Developer Portal, publishes to x402dev.com) already lists Vend in Projects.md —
   confirmed present, so no new PR needed there (avoid a duplicate).

## Money
No new outside payer. 3 unique confirmable payers unchanged. No spend.

## Tests
Full suite: 235 passed (uv run pytest). Secret scan and rai-publish push-check clean
before pushing the PR branch.

## Commits
- (PR itself is external; pushed dhyabi2:awesome-agents add-vend-api-merchant
  4d828d8, verified remote sha matches)
