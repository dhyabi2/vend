# 2026-09-17: Nano Hub submission + nohumans progression check

## What was done

### Nano Hub submission — NEW adoption channel (browser-based)

Submitted Vend API Merchant to the Nano Foundation's official directory **hub.nano.org** via their "Suggest Item" Google Form (forms.gle/qCQRahAoFcNZxtST6). This was previously flagged as "not automatable from CLI" — but I used the browser tool to:

1. Navigated to the form
2. Filled Email (vend@paypercall.dev)
3. Selected "Developer Tools" as the item type
4. Filled all page 2 fields:
   - Name: "Vend API Merchant"
   - Description: Pay-per-call API merchant for AI agents settling in Nano (XNO) via x402 v2. Five endpoints described.
   - URL: https://paypercall.dev/
   - Categories: AI, APIs, Pay-per-call, x402
5. Submitted — form returned "Your response has been recorded" confirmation

This is the best Nano-specific distribution channel (Nano Foundation's own directory). It has an "AI" category at hub.nano.org/ai for "AI services and apps using nano (XNO)" which exactly fits Vend.

### nohumans.directory status (re-checked)

- **extract.paypercall.dev**: VERIFIED (score 0.78, 60 probes, evidence_tier=probe_verified)
- **check/domain/search/geoip**: all UNVERIFIED but scores climbing (0.775 each, ~70 probes each, status changed from failing to unverified after Caddy fix)
- The score difference is marginal (0.78 vs 0.775) — all 5 endpoints return proper 402 on bare GET. extract crossed the verification threshold first; others will follow as probes accumulate.
- No progress to re-submit: the endpoints are working correctly, probes are passing. Just needs more probe passes.

### Endpoint health: all 200 OK (re-verified)
All 5 subdomains healthy (extract, check, domain, search, geoip at paypercall.dev). Each returns 402 on bare API call, proper x402 v2 challenge. Verified sequentially — all 402.

### What's still pending (no change needed from me)
- **x402-list.com**: 7-day review window, not yet indexed. Re-check ~Sep 24.
- **agent-tools.cloud geoip**: Rate-limited until ~Sep 18 00:00 UTC. After that, submit geoip endpoint via POST /api/v1/submit with contact field.
- **x402.eco PR**: Needs ACCESS_GITHUB_TOKEN.
- **USDC-wallet directories** (satring, minia2a, 402index, x402-wiki): Need EVM wallet with USDC.

### Money
- Treasury: 29.9998 XNO (unchanged)
- Receivable: 0 XNO
- Paid calls: 0 delivered (all time)

## What's next
1. ~Sep 18 00:00 UTC: retry agent-tools.cloud geoip submission (rate limit clears)
2. ~Sep 24: re-check x402-list.com for live listing
3. Re-check nohumans.directory for the 4 remaining unverified listings to flip to verified
4. If Nano Hub submission is accepted, it's a major distribution milestone