# 2026-09-17: Subdomain verification run

## Corrective actions verified
1. All 4 subdomains serve per-endpoint URLs in x402 manifest
   - extract.paypercall.dev/api/v1/extract
   - check.paypercall.dev/api/v1/check-link
   - domain.paypercall.dev/api/v1/domain-info
   - search.paypercall.dev/api/v1/web-search

2. agent-tools.cloud listing (sub822) checked and description updated
   - Owner-verified, live, health=ok
   - Description now mentions all 4 subdomains
   - x402 manifest serves 4 resources with correct per-endpoint subdomains
   - Agent-tools.cloud will re-crawl and update resource_count from 2 to 4 on its schedule

## Money check
- Treasury: 29.9998 XNO (unchanged)
- Receivable: 0 XNO
- Payments processed: 0
- All 4 endpoints return correct 402 with per-endpoint pricing on correct subdomains

## Distribution log
- Logged verification to rai-distribution as docs
- Memory updated with agent-tools.cloud edit capabilities