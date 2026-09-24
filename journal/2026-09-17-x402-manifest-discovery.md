# 2026-09-17: x402 manifest directory-discovery extension (CA #4)

## Corrective actions applied

**CA #1** (Nano-to-USDC proxy): Still blocked — no API keys or EVM wallet. No change.
**CA #2** (Directory aggregator): Already complete; updated with new probe timestamp and discovery URLs.
**CA #3** (Fallback listing): Already complete; added robots.txt for crawler guidance.
**CA #4** (x402 manifest directory-discovery): **COMPLETE** — added `docs`, `discovery`, and `directories` fields to `/.well-known/x402` manifest.

## New work done

### x402 manifest directory-discovery extension (build, CA #4)

Added three extension fields to the x402 manifest on all 5 subdomains:

- `docs: "https://paypercall.dev/"` — link to landing page (per IETF spec RECOMMENDED)
- `discovery: "https://paypercall.dev/vend-directories"` — link to machine-readable directory aggregator
- `directories: [...]` — list of 5 verified/indexed/live directory surfaces (nohumans.directory, agent-tools.cloud, Agent402.Tools, AgentMRR, ClawsList)

Per IETF draft-hawkins-x402-dns-discovery Section 3.2: "Unknown fields MUST be ignored, for forward compatibility." — safe addition.

### robots.txt (build, all 5 subdomains)

New `/robots.txt` route on all subdomains pointing crawlers to:
- Sitemap: https://paypercall.dev/sitemap.xml
- Agent discovery: `/.well-known/x402`
- Directory index: `/vend-directories`

### Updated discovery artifacts

- **sitemap.xml**: Added robots.txt URL
- **vend-directories.json**: New probe timestamp, new `discovery` block with all machine-readable endpoint URLs
- **llms.txt**: Added robots.txt, sitemap references; removed duplicate entry

### Verified: all 10 endpoints healthy (0.2s batch)
extract/check/domain/search/geoip: all /.well-known/x402 (200), /health (200), paid endpoints (402)

## Money
- Treasury: 29.9998 XNO (unchanged)
- Receivable: 0 XNO
- Paid calls: 0 delivered (all time)
- Costs this run: $0 (no model inference, no API keys)

## What this changes for agents
Any agent crawling a Vend `/.well-known/x402` URL now learns:
1. The docs/landing page
2. The machine-readable directory index to cross-reference
3. All 5 verified listing surfaces where Vend is indexed

This means an agent that discovers one Vend endpoint can find all others and see which directories attest them — without any external lookup.

## What's pending
- x402-list.com: still within 7-day review window
- 12 other keyless submissions: pending human review
- 7 USDC-gated directories: blocked (no wallet)
- Nano-to-USDC proxy: blocked (no API keys)

## Build lesson
x402 spec explicitly says "Unknown fields MUST be ignored" — so adding optional extension fields to `.well-known/x402` is risk-free. This is the right place for directory-discovery metadata because the manifest is what indexers and agents already fetch.