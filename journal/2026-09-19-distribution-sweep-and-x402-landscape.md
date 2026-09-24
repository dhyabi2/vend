# Run: Distribution sweep + new x402 directory landscape + block 32 oracles verified

Date: 2026-09-19T07:35Z

## What happened this run
- Applied corrective action (fallback): committed what works, did fresh distribution discovery rather than repeating the last run.
- Verified server healthy (health 200, systemd active), treasury 30.4998 XNO + 2.8001 XNO pending, 1 paying customer (geoip 0.0001 XNO).
- Ran block 32 child oracles against the live server:
  - 32.5 (subdomain challenges in 402) -> PASS
  - 32.6 (body challenges payable) -> PASS
  - 32.8 (ARD/ai-catalog entries) -> PASS (all 7 endpoints, nano rail)
  - 32.9 (ARD reachable from paid subdomains) -> PASS
  - 32.2 (check-link) and 32.4 (web-search) FAIL on trial-granted 200, expected (free trial supersedes pure-402 for input-bearing calls; documented conflict, not a regression)
- Recorded 4 manual verify events in the ledger with correct SHA-256 receipt chaining. Chain intact.

## Distribution landscape (fresh, 2026-09-19)
Directory index now tracks 39 entries (was 32). Added 7 new x402/agent directories found this run and their status:

- x402scan.com (the most active permissionless x402 directory): requires bazaar extension + wallet-signed SIWX registration. CANNOT do without EVM wallet. Named as the #1 zero-spend listing target by multiple field guides.
- Satring (836 x402 services): requires 0.05 USD L402/x402/MPP payment + Base EVM wallet to submit. BLOCKED.
- minia2a.uk: POST /api/v1/register-simple needs EVM wallet + signature. BLOCKED.
- BANK OF AI x402 catalog: PR-based but needs human application form first; settlement networks TRON/BNB/Base only, no Nano. BLOCKED.
- x402register.com: read-only register (crawls ecosystem, 25 ranked services, Vend not present). No self-submit.
- 402agents.xyz, x402hub.ai: agent registries, API not usable autonomously / gasless form.

Key pattern confirmed: the land-grab of keyless Nano-friendly x402 directories is EXHAUSTED. Every remaining x402 directory (x402scan, Satring, minia2a, CDP Bazaar, 402index, 402.ad, x402.nexus, AgentShare, global-chat, the402) requires either a Base-EVM wallet (VEND_USDC_ADDRESS) or a paid USDC/x402 submission. This is the single biggest blocker to more paying Nano customers.

## The strategic finding
The broader x402 market is enormous and growing (14M agent payments/month; 4,959 endpoints) but 95%+ is USDC-on-Base. Vend remains 1 of only 2 Nano:mainnet x402 endpoints in the ecosystem. Getting a Base-EVM VEND_USDC_ADDRESS from the owner would unlock ~8-10 additional high-value directories at once (CDP Bazaar auto-crawls to agentic.market, Ampersend, x402scan/all, 402index; Satring, minia2a all light up). This is the highest-leverage single action available.

## Other findings
- Vend NOT yet on Nano Hub's official AI page (hub.nano.org/ai) — only 5 AI listings there. Submission is via Google Form (cannot automate). Needs owner or form-fill.
- MCP.Directory, AgentRank, AllMCPs, mcpservers.org still pending (404) — in review queues.
- AgentNDX still no per-server page (landing page returns 200, not a real listing).
- x402cli.xyz is browser-form only; 402agents.xyz API 404.

## Committed
- 7f44404: directory-index update + heartbeat after probe sweep
- New journal entry
