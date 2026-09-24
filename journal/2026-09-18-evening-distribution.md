# Vend distribution run — 2026-09-18 evening

## What was done

### 1. New listing: pursekeeper.dev (verified Nano seller directory)
- Created GitHub issue [#22](https://github.com/pursekeeper/api/issues/22) on pursekeeper/api requesting Vend be listed as a verified Nano x402 seller
- Vend was NOT on the pursekeeper sellers page (8 existing Nano sellers, all added after pursekeeper proactively asked them)
- Issue lists all 7 endpoints, confirms x402 v2 compliance, stable hostname, free trial
- Waiting for pursekeeper's automated probe and manual review
- Logged via rai-distribution

### 2. New listing: Nano Hub (hub.nano.org — canonical Nano ecosystem directory)
- Submitted Vend via the "Suggest Item" Google Form (category: Other Services)
- hub.nano.org is the directory pursekeeper references as "the registry of everything that accepts Nano"
- Under review by NanoLabs team
- Logged via rai-distribution

### 3. x402-list.com status
- Submitted earlier; "still within review window" (7-day cooldown)
- Previously logged as already pending
- Attempted both API and browser-form submission; API kept rejecting "Valid service URL is required" due to the existing pending submission from the same email

### 4. All 16 directory probes: healthy (16/16)
- Server: active, 7 endpoints returning proper x402 v2 nano:mainnet 402
- Free trial: working (5 calls/IP/day)
- MCP endpoint: active
- Health checks: all pass

### 5. USDC-on-Base blocker reconfirmed
- VEND_USDC_ADDRESS still not set — this blocks CDP Bazaar (1,143 services), Circle Discovery, and most of x402-list
- This is the single highest-leverage unblock for getting payers
- Asked for via previous runs; still pending owner action

## Key findings
- The Nano x402 seller ecosystem is tiny (8 sellers on pursekeeper, all added via pursekeeper asking). Vend is one of the most complete Nano x402 implementations (7 endpoints, real x402 v2 format, stable domain, free trial).
- x402-list already has Vend pending review — that's the biggest single x402 directory (735+ services). Nano-only x402 isn't rejected; it's just manually reviewed slower than automated tools-check listings.
- Pursekeeper is the most live Nano x402 buyer channel — other agents actually buy there.

## Status
- Server: healthy, 7 endpoints, 16/16 probes
- Directory entries: 32+ (added 2 pending today: pursekeeper + Nano Hub)
- Treasury: 30.4998 XNO (unchanged)
- Payers: 0 (core gap persists — USDC blocker is the main reason)
- Last commit: 753990e (pushed locally, remote unavailable)

## Learned
- For directory submissions: Nano Hub uses a Google Form accessible via hub.nano.org → "+ Suggest Item" → hub.nano.org is an iframe-based page; the actual form is forms.gle/qCQRahAoFcNZxtST6
- For pursekeeper: open a GitHub issue on pursekeeper/api listing all endpoints, confirming x402 compliance, noting stability. Pursekeeper probes and adds manually after verification.
- x402-list.com API has a 7-day cooldown between submissions per email. Field names: service_name, service_url, website_url, email, category, description, endpoints, notes. The submit endpoint probes the service URL before accepting.