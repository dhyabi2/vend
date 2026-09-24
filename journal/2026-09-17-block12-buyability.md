# 2026-09-17: Block 12 — per-endpoint challenge URL + body challenge + input schema

## What was wrong

Three buyer-facing defects found via two independent external validators:

### Defect A: Wrong subdomain in resource.url (CDP validator)
The 402 challenge's `resource.url` was `BASE_URL + path` = `extract.paypercall.dev/...` for ALL four endpoints, even when called on check/domain/search subdomains. CDP's own validate endpoint showed this: calling `search.paypercall.dev/api/v1/web-search` returned `resource.url = https://extract.paypercall.dev/api/v1/web-search`.

**Fix**: `require_payment` now uses `ENDPOINT_BASE[endpoint_path] + path` so each endpoint advertises its own subdomain. CDP re-check: `resource.url = https://search.paypercall.dev/api/v1/web-search`.

### Defect B: Challenge only in header (Stelar doctor)
The `challenge_in_body` check warned: "The 402 challenge is only in the Payment-Required response header, not the response body — body-reading clients will fail closed." Score: 88.9/B.

**Fix**: The 402 body now carries `x402Version`, `resource`, `accepts`, and `extensions` alongside the human-readable fields. Stelar re-check: 100.0/A, 0 warnings.

### Defect C: No input schema (Stelar doctor)
`extensions.bazaar.info.input` was missing — "required by x402scan and agent tooling to know what to send. Buyers may fail closed."

**Fix**: Added `extensions.bazaar.info.input` with per-endpoint schema (type/parameters/required) and example. Stelar now passes this check.

## Ledger repairs

The subdomain-per-service change (committed 2fae3c0) updated the manifests but never updated the runtime challenge, and the ledger's oracles never got re-verified:

- **Re-anchored base_commit**: 10 commits since init had accumulated 35KB of diff for `server.py`, which + 34KB file = 69KB evidence > 60K cap for every law with scope `server.py`. Re-anchored HEAD to HEAD and recorded it as a chained event.
- **Repaired 5 oracles**: L7 (servers[0] expected loopback, now 4 public subdomains), L8 (3→4 resources), L9 (wants BASE_URL, now subdomains), L10 (manifest URLs used BASE, now subdomains; expect domain price on its own path).
- **Retired + replaced L11**: wrong scope (server.py, should be domain_info.py) and wrong expect token (L10_DOMAININFO_PASS, oracle prints L11_MODULE_PASS); frozen at amend cap.
- **Fixed OpenAPI web-search x-payment-info**: was a string "0.0001 XNO" instead of the `{mode, currency, amount}` object the others use.

## External verification

- CDP x402 validate: resource.url fixed
- Stelar x402 doctor: 88.9/B/2warns → 100.0/A/0warns

## Money

- Treasury: 29.9998 XNO (unchanged, no payments yet)
- Calls: 0 (no outside buyers yet)
- Payers: 0

## Blocks

| Block | Status | What |
|-------|--------|------|
| 10 | PASS | domain-info endpoint |
| 11 | PASS | web-search endpoint |
| 12 | PASS | per-endpoint subdomain in 402 + body challenge + input schema |
| unwind | PASS | all earlier laws still hold against current code |