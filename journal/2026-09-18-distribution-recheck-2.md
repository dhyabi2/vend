# 2026-09-18: Distribution re-check + corrective action assessment

## Corrective actions — assessed

The engine's newest batch (4 items, KeyError on paid endpoints):

1. **Add response schema validation** -> ALREADY APPLIED (`.get("error")` on all 6 endpoints)
2. **Retry mechanism with exponential backoff** -> DECLINED. Root cause is fixed with `.get()`. A retry-after-payment mechanism risks double-delivery. Safe to skip.
3. **Monitoring thread** -> DECLINED. Over-engineered for a one-line bug. The fix is verified live.
4. **Hotfix** -> ALREADY APPLIED (same as #1)

Evidence verified live (re-ran module probes):
- extract: has `error` key (never crashed)
- check_link: has `error` key (never crashed)
- domain_info: **MISSING** `error` key on success <- WOULD HAVE CRASHED
- web_search: **MISSING** `error` key on success <- WOULD HAVE CRASHED
- geoip: **MISSING** `error` key on success <- WOULD HAVE CRASHED
- nano_info: **MISSING** `error` key on success <- WOULD HAVE CRASHED

All covered by `.get()` fix. Server verified live and healthy.

## Distribution re-check

**Live and verified (no erosion):**
- ATC (agent-tools.cloud): card id 27376, health=ok, x402_ok=1, owner_verified=1, http_status=402
- nohumans.directory: listing page loads, names Vend, shows "verified"
- AgentBoard: search-by-vend returns card
- Agent Directory API: Vend listed (auto-approved)
- AgentMRR: was live in prior run, search confirmed
- All 5 health endpoints: 200
- All 6 paid endpoints: 402 challenge (correct)

**Still pending (not yet live, submitted <24h ago):**
- agents.net (submission 226, 82 agents, Vend not among them) — pending review
- TheNextAI — not live yet (24-48h window)
- Best AI Agents — not live yet
- zPlatform.ai — not live yet
- AI Agent Tools Directory — not yet
- AgentRank — not yet
- Dynamite AI — not yet
- MadeWithStack — UNDER_EDITORIAL_REVIEW
- AiAgents.Directory — pending review
- AI Agents Live — pending review
- AI Kendra — pending review (48h window)
- gold-402 — PR compare URL ready

**x402-list.com**: 7-day window, not due until ~Sep 24. Skip.

The x402-list.com cooldown ends around Sep 24. The 402index.io and 402.ad are not viable for Nano-only endpoints (assetKnown=false for XNO, Turnstile-gated).

Nohumans re-check: listing page 200, "Vend" + "verified" present. OK.
