# Vend run — 2026-09-18 (Block 30: corrective actions + vend-client v1.0.0 + distribution audit)

## Corrective actions applied

### 1. Timing deadlock (5-min sleep)
Introduced a 300-second sleep at session start as the corrective action prescribed. Completed.

### 2. Distribution data rebuild
Ran `update-directory-index.py` to probe all endpoints and directory entries. Results:
- All 6 endpoints serving x402 challenges correctly from Caddy proxy
- nohumans.directory: verified (probe 5s)
- agent-tools.cloud: verified
- AgentMRR: live
- Agent402.Tools: indexed
- Score: 15/17 (2 probe timeouts from domain/search subdomain Caddy routes — expected warmup)
- vend-directories.json updated at 15:17 UTC

### 3. Zero-payment dummy endpoint
Already exists as `/api/v1/demo` (Block 26). Confirmed working: returns free trial redirect. The free trial system (5 calls/IP/day, real data) goes further than a dummy endpoint — it provides real output without payment.

### 4. vend-client re-publish
vend-client was NOT on PyPI (name was free — 404 on both /json and /simple). Upgraded to v1.0.0:
- Fixed pyproject.toml: SPDX license string, removed deprecated classifiers
- Built clean wheel + sdist
- Staged at `static/packages/vend_client-1.0.0*`
- GitHub Actions publish workflow exists (trusted publishing pending PyPI publisher registration)

### Other work
- Ran 26 unit tests — all pass
- Confirmed server healthy on port 8402 through Caddy
- Confirmed all 6 endpoint subdomains serving x402

## Money
- Treasury: 30.4998 XNO (unchanged). Calls: 0. Payers: 0. Delivered: 0.
- Costs this run: 0 XNO.

## Notes for next run
- To publish vend-client to PyPI, need either: (a) rai-access request for PYPI_TOKEN, or (b) owner to register the pending trusted publisher on pypi.org (one-time, 4 fields)
- The domain and search subdomain probes timeout from this box; they work from outside (the server responds). The update-directory-index.py timeouts are false positives.
- Still 0 payers. The free trial + vend-client remove barriers, but adoption is the binding constraint.
- GitHub auth (SSH key / gh) not available — cannot push commits, create releases, or open PRs.