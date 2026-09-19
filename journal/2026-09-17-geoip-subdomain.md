# 2026-09-17: Geoip dedicated subdomain + distribution sweep 2

## Work done

### Geoip.paypercall.dev subdomain fix (per corrective action)
- server.py: changed `GEO_BASE = EXTRACT_BASE` to `GEO_BASE = "https://geoip.paypercall.dev"`, removed stale DNS-TODO comment (lines 65-68)
- landing.html: 3 references fixed (endpoint list, curl example, Stelar Doctor conformance link)
- llms.txt: geoip URL from extract to geoip subdomain
- README.md: Stelar Doctor geoip link from search to geoip subdomain
- Server restarted (systemctl restart vend-api)
- Verified: ALL 5 endpoints return 200 on /health (--resolve method per owner's correction)
- x402 manifest now advertises correct subdomain URLs for all 5 endpoints
- Agent402.Tools: geoip.paypercall.dev auto-indexed (origin register returned listed=true, toolCount=5, routable=true, health=1)

### Distribution
- Agent-tools.cloud geoip submission: RATE LIMITED (5/day, retry ~2026-09-18 00:00 UTC)
- x402.eco PR: still blocked (no ACCESS_GITHUB_TOKEN)
- x402-list.com: still pending (~5h ago, 7-day window)

### Money
- Treasury: 29.9998 XNO (unchanged)
- Receivable: 0 XNO
- Paid calls: 0 delivered (all time)
- All 5 endpoints returning correct 402 with per-endpoint pricing on dedicated subdomains

## What's next
1. Agent-tools.cloud geoip submit: retry after rate limit clears (~Sep 18 00:00 UTC)
2. x402.eco ecosystem PR: needs ACCESS_GITHUB_TOKEN
3. x402-list.com: re-check around Sep 24
4. Paid calls: still 0 — the most urgent problem remains unsolved