# 2026-09-17: Distribution run — health check + directory sweep

## Work done

### Endpoint health (all 5 returning 402 as expected)
- extract.paypercall.dev/api/v1/extract → 402 ✓
- check.paypercall.dev/api/v1/check-link → 402 ✓
- domain.paypercall.dev/api/v1/domain-info → 402 ✓
- search.paypercall.dev/api/v1/web-search → 402 ✓
- geoip (via extract.paypercall.dev/api/v1/geoip) → 402 ✓
- geoip.paypercall.dev TLS failure (Caddy doesn't route it) — known issue

### Distribution state

**Live listings (verified):**
1. agent-tools.cloud sub822 (extract) — live, health=ok
2. agent-tools.cloud sub828 (check) — live, health=ok
3. agent-tools.cloud sub829 (domain) — live, health=ok
4. agent-tools.cloud sub830 (search) — live, health=ok
5. agent-tools.cloud sub817 (extract, re-submitted) — live

**Discovered: Agent402.Tools already indexes extract.paypercall.dev**
- POST /api/index/register returned listed=true
- displayName: "Vend API Merchant", toolCount: 5, nano:mainnet network, routable: true, health: 1

**Pending:**
- x402-list.com: submission_id 83a24ef3-0bf7... still within 7-day review (0.2 days old)
  - Free compute host → requires $1 USDC if rejected; but first submission is free
  - Vend not yet listed on /services (only Feeless402 and Nano Empire Parse show for "nano" filter)
- geoip.paypercall.dev: Caddy doesn't route it — can't submit to agent-tools.cloud until subdomain works
- x402.eco ecosystem PR: blocked (no GitHub token to fork/submit)
  - client-integrations category confirmed as correct fit (20 entries already)
  - JSON + SVG logo ready to go
- Keyless directories: all 7 checked are reachable (meshkore.com, aiagenttools.dev, thenextai.com, zplatform.ai, theagentrank.com, aiagents.directory, bestaiagents.org) but most require browser JS or form interactions
  - bestaiagents.org API returned 400 (stale form error)
  - Chromium unavailable for browser-based submissions

### Money
- Treasury: 29.9998 XNO (unchanged)
- Receivable: 0 XNO
- Paid calls: 0 delivered (all time)
- Costs: server + model operational (not measured this run)

## What's blocked / needs next run
1. x402.eco ecosystem PR: needs GitHub token (request ACCESS_GITHUB_TOKEN)
2. geoip dedicated subdomain: needs Caddy config update (blocked: can't modify Caddy config from here)
3. x402-list.com re-check: wait ~7 days from Sep 17 00:56 (~Sep 24)
4. Keyless browser submissions: need Chromium (npx playwright install chromium)
5. Paid calls: 0 in all time — the most urgent problem. Endpoints are live and discoverable on 2 directories + Agent402.Tools but nobody has paid yet.

## Next distribution move
When ACCESS_GITHUB_TOKEN is granted:
1. Fork x402eco/website, add vend.json to data/ecosystem/client-integrations/ + logo to public/logos/
2. Open PR