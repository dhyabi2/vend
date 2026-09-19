# Distribution: agent-tools.cloud gap closed

Date: 2026-09-17

## What was done

The run brief said distribution gap on agent-tools.cloud (only extract endpoint listed, 1/5) and x402-list.com
pending. This run:

### agent-tools.cloud — submitted 3 new listings
- **check.paypercall.dev** → sub828, auto-verified live, HTTP link checker
- **domain.paypercall.dev** → sub829, auto-verified live, domain intelligence
- **search.paypercall.dev** → sub830, auto-verified live, web search

All 3 were claimed (domain ownership verified) using the token-cycling method through the shared
state/agent-tools-verify.txt file: server serves from one file, so for multi-domain setups you cycle
the file contents one claim at a time (write token, wait ~2s for propagation, verify claim, next).

Descriptions PATCH-ed for all 3 after claim verification.

### x402-list.com
- Still within 7-day review window (submission_id 83a24ef3 from earlier run)
- Re-submit refused with 429 until ~2026-09-24

### Geoip (L20/L21)
- Rate-limited on agent-tools.cloud (5/day) — needs separate submission in next run
- Works on extract.paypercall.dev/api/v1/geoip, no dedicated subdomain yet
- geoip.paypercall.dev DNS resolves but Caddy doesn't route it

### Key finding: agent-tools.cloud claim flow for multi-domain
The PATCH endpoint `/api/v1/listings/{kind}/{slug}` needs `not_verified_owner` resolved first.
Workflow:
1. POST `/api/v1/claims` with `host` and the `well-known` token
2. Write claim token to the server's verify file
3. POST `/api/v1/claims/{id}/verify` with the token
4. Now PATCH succeeds

Since all subdomains serve from the same vend-api, the verify file must be swapped for each claim.
The original token was restored afterwards.

### Outstanding
- x402-list.com listing still pending (re-check ~2026-09-24)
- geoip endpoint needs own agent-tools.cloud submission (retry 18h)
- Agent402.Tools register (keyless, already done from earlier run)
- No paid calls yet — 0 delivered in any endpoint
