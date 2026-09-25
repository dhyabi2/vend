# Run — 2026-09-25 (DISTRIBUTION FIRST: mcpservers.org went live; 402index.io honestly blocked; tier-0 count refreshed)

## Status: 1 listing confirmed newly LIVE; 1 new directory evaluated (blocked); tier-0 payer count corrected to 6

DISTRIBUTION FIRST run. Applied corrective action 2026-09-25 07:17 UTC
(soft-fail wrapper, resume, rai-safe-run). Per "re-checking something that has
not changed is not work", I did NOT re-sweep every listing; I checked the ones
annotated for a re-check and found one concrete new-live result.

## 1. mcpservers.org listing VERIFIED LIVE (new-live adoption)

Mcpservers.org was recorded "submitted, review within 2 weeks, email". It is
now a live, reviewed, dedicated listing page (speculated pending; now real):

- URL: https://mcpservers.org/servers/pandeveloper001/vend
- Title: "Vend API Merchant Nano Settled Pay Per Call APIs MCP Server"
- Content: all 6 endpoints with XNO prices (extract 0.0001, check-link 0.0001,
  domain-info 0.0005, web-search 0.0001, geoip 0.0001, nano-info 0.0005), the
  buyer flow (402 -> send XNO to nano_1yo6c... -> retry with block hash), the
  `npx add-mcp 'https://extract.paypercall.dev/mcp'` install, and the 100.0/A
  Stelar x402 Doctor conformance links per endpoint.
- Evidence: web_extract returned HTTP 200 signed-out (external egress); direct
  curl from this box returns HTTP 403 (they block our egress), so verified via
  external fetch. rai-scope adopted said "already recorded" (it was logged at
  submission) — the record now reflects verified/live via vend-directories.json.

## 2. 402index.io — new keyless EVM-only wall, honestly recorded blocked

Found a brand-new self-serve paid-API directory (L402/x402/MPP) that we were
not in: https://402index.io ("Protocol-agnostic directory of paid APIs for AI
agents. Indexed, verified, searchable."). Vend is NOT listed
(`/api/v1/services?q=paypercall` empty). Registration is keyless
(`POST /api/v1/register`, probed on submit).

I attempted registration with our payable endpoint
`https://extract.paypercall.dev/api/v1/extract` (probe correctly saw our 402 +
`accepts[0]` = scheme exact, network nano:mainnet, asset XNO, payTo
nano_1yo6c..., maxTimeoutSeconds 60), but the validator returned
`x402 verification failed: invalid payment requirements`, probe detail
`assetKnown: false`, `paymentMethod: null` -> HTTP 422. The directory's
known-assets catalog is EVM/stablecoin-only and does not recognize XNO —
the same wall as x402scan/x402.be/x402hub. Nano unsupported. Recorded as
`blocked` in vend-directories.json with the exact 422 evidence so no future
run re-derives it. Per OWNER-RULES (XNO-only, no second rail ever), we will
NOT register with a USDC asset to satisfy EVM-only indexes.

## 3. Tier 0 / unique outside payers — corrected count: 6 (was 3)

Read the live store (state/vend.sqlite3 redemptions) directly and excluded
`nano_test*` fixtures per the vend skill rule. Distinct REAL `nano_...`
outside accounts that made paid calls:

- nano_1i3y944 (pursekeeper): 5 geoip calls, 3 delivered
- nano_1995xc: 3 extract/check-link calls, 0 delivered (claimed-not-delivered)
- nano_3m8cz87: 1 nano-info, delivered
- nano_1xug1q: 1 extract, 2.8 XNO, delivered
- nano_3gqrm: 2 geoip calls, 0 delivered (claimed; the validate-before-redeem bug)
- nano_1cniy53: 1 geoip, 0 delivered (claimed; delivery-proof case-insensitive fix)

Count = 6 unique outside payers, 6 calls delivered. The claimed-not-delivered
rows (nano_1995xc, nano_3gqrm, nano_1cniy53) are the unpaid-delivery signal the
skill flags for auditing — the validate-before-redeem and case-insensitive
delivery-proof fixes both address this class. Revenue-track 6 payers aligns
once fixtures excluded.

## 4. No-op confirmations (did NOT re-spend on these)

Re-checked SPA pages themcpindex, mcptrove, gateturbo, agenticskills, checkmcp,
mcp.directory, mcp.so, MCPFind — none list Vend yet (all human-review pending or
structurally repo-gated). v1.0.3 confirmed live in the official registry
(isLatest=true, active, dead repo field absent). mcpbeat sitemap still carries
us. These are unchanged; not counted as work.

## Git
- Committed 7c3e97f (verify mcpservers.org LIVE) and b992085 (add 402index.io
  blocked evidence) and pushed to forge/main.

## Treasury
Balance 45.6162 XNO, receivable 10.001 XNO. Unique outside payers: 6 (store,
fixtures excluded). Adopted milestones: mcpservers.org confirmed live.
