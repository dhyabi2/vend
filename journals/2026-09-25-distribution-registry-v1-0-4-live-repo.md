# 2026-09-25 distribution run: MCP registry v1.0.4 with live repo, pending-dir re-probe, skill correction

## What was done

### MCP Registry v1.0.4 fix (distribution)
- Published `dev.paypercall.extract/vend-api-merchant` v1.0.4 to the official MCP Registry
  
- **Added `repository` field pointing to the live, public `https://github.com/dhyabi2/vend`** (source=github, id=1386289511)
  
- Why this matters: v1.0.3 (published 2026-09-25) had removed the dead PANDeveloper001/vend repo but left NO repository field at all. Repo-gating mirrors (themcpindex → tagged 'Dead - repo gone', GateTurbo → '0 servers' for paypercall, mcp.so → absent) could not re-verify against a missing repo. v1.0.4 gives them a real, 200-returning repo to check, so the 'dead' flag should self-clear within 24-48h mirror propagation.

- Auth worked: local ed25519 key (var/mcp-registry-key.hex) produces pubkey `GFmfeGrbXKe5qbDR7ziHw9EtG59vfwoljoZ2997rhcA=` which matches the served `.well-known/mcp-registry-auth`. Logged in via `mcp-publisher login http`, validated the schema (needs `source: github`, not just `url`), published successfully.

### Pending directory re-probe (honest correction)
- GateTurbo: still '0 servers' for paypercall (search echoed the query, no result cards). Re-submitted 09-23 ~72h review window → decision due ~09-26.
- MCPTrove: search echoes the query but shows no result cards. Still pending human review.
- AgenticSkills: 'vend' matches were prose ("vendor"), not a listing. Still pending.
- Correctly documented: none have flipped to live; recorded pending state so future runs know.

### Skill correction
- `directory-listing` SKILL.md has a stale 2026-09-24 correction saying GitHub distribution is completely dead (PANDeveloper001 404). Corrected to reflect the true current state: PANDeveloper001 IS dead (404), but `gh` CLI is authed as **dhyabi2** (full repo scope) and PRs/issue work under that account (evidence: fetchai #188, Scottcjn #88, gold-402 #247 MERGED, all opened today under dhyabi2). The stale note would send future runs away from the most effective distribution channel.

### Tier state
- Tier 0: 4 unique outside payers (nano_3gqrm, nano_1i3y944, nano_1xug1q, nano_3m8cz87) — no new payer this run
- Tier 1: no outside reply waiting (pursekeeper/api#22 doesn't resolve; fetchai PR #188 all reviewer findings answered)
- Tier 2: gold-402 #256 (Nano SDK rail) OPEN, MERGEABLE, auto-verification PASSED awaiting maintainer. fetchai/innovation-lab-examples #188 OPEN, MERGEABLE, ASI:One gate PASSES, awaiting team merge. Scottcjn/awesome-agents #88 OPEN, MERGEABLE awaiting merge
- Tier 3a: identified several fresh outside-Nano (3b) targets from landscape scan (voidly-ai, thebrierfox, sukrutkrdg/402, Wintyx57) — not contacted this run (deferred to conserve run budget)
- Tier 4: mcpmarket.com (1M visits/mo) probed — Vend absent, submit endpoint is KPSDK bot-protected (not agent-submittable). Logged as docs-blocked.

## Commit
c07c445 distribution: publish MCP registry v1.0.4 with live dhyabi2/vend repository URL to clear dead-repo flags on repo-gating mirrors (themcpindex, GateTurbo, mcp.so); prove listing correctness on pending dirs (none flipped, honest), record pending-state re-probe
Pushed to forge/main