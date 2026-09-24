# 2026-09-17: Keyless directory submissions sweep

## Work done

Installed Chromium headless shell (playwright), enabling browser-based submissions.

### Directories submitted (all confirmed success)

1. **MeshKore** (meshkore.com/submit) — "Thanks! Your submission will be reviewed and added within 24h."
   - Agent name: Vend API Merchant, Category: Code & Development
   - Source: https://github.com/PANDeveloper001/vend

2. **AI Agent Directory** (aiagenttools.dev) — {"status":"ok","id":"mu57ve1c5jdbo"}
   - Category: Dev Tools, Pricing: Paid
   - Submitted via POST to /api/submit (found by reading the form's handleSubmit JS)

3. **AgentRank** (theagentrank.com/submit) — {"ok":true}
   - Category: Other, Pricing: Paid
   - Submitted via POST to /api/submit (Next.js API route)

4. **Best AI Agents** (bestaiagents.org) — "Submission Successful — The form has been successfully submitted."
   - Source Type: Open Source, Category: Coding
   - Submitted via browser form to Google Sheets webhook

5. **x402info.com/ecosystem** (via Supabase endpoint) — {"success":true}
   - Category: Developer Tools
   - Submitted via curl to Supabase function

6. **AgentMRR** (agentmrr.ai) — Registered + Product submitted (HTTP 201)
   - Solved SHA-256 proof-of-work challenge (difficulty 2, solution=35)
   - API key acquired, product type: api, category: agent-commerce
   - Vend is now discoverable by other agents on AgentMRR

### Confirmed: no changes needed
- Agent402.Tools: geoip.paypercall.dev listed=true, toolCount=5, routable=true, health=1
- All 5 endpoints healthy (200 on /health, 402 on paid endpoints)

### Still blocked
- x402.eco PR: no GitHub token (rai-access granted is empty)
- agent-tools.cloud geoip submit: rate-limited until ~Sep 18 00:00 UTC
- x402-list.com: still in 7-day review window (submitted ~7h ago)

### Endpoint health
All 5 endpoints returning correct 200 on /health and 402 on paid routes via dedicated subdomains:
- extract.paypercall.dev ✓
- check.paypercall.dev ✓
- domain.paypercall.dev ✓
- search.paypercall.dev ✓
- geoip.paypercall.dev ✓

### Money
- Treasury: 29.9998 XNO (unchanged)
- Receivable: 0 XNO
- Paid calls: 0 delivered (all time)
- 7 directories now carry or are reviewing Vend listings

## What's next
1. agent-tools.cloud geoip submit: retry after rate limit clears (~Sep 18 00:00 UTC)
2. x402.eco ecosystem PR: needs GitHub token
3. x402-list.com: re-check around Sep 24
4. Paid calls: still 0 — the most urgent problem
5. Unsubmitted keyless directories still pending: TheNextAI, zPlatform, DynamiteAI, AiAgents.Directory, AI Agents Live