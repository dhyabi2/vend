# 2026-09-17: Block 13 — Buyer-ready integration examples + conformance evidence

## What was done

All 12 earlier blocks pass, but 0 paid calls. The gap is buyer trust and friction: a
buyer landing on the page had no working code example and no evidence that paying gets
a result.

### Changes

1. **New: `examples/python-buyer.py`** — standalone Python script showing the exact 3-step
   x402 flow: unpaid 402 → parse challenge → pay → retry with block hash. Supports all
   four endpoints. Works with `feeless402` CLI or manual payment input.

2. **Landing page (`static/landing.html`)** — major buyer-facing upgrades:
   - Python quick-start snippet alongside the existing curl example
   - Stelar 100.0/A conformance badge in the header tags
   - Conformance section with links to all four endpoints' Stelar doctor results
   - Bazaar input spec and per-endpoint subdomain badges
   - Link to `examples/python-buyer.py` on GitHub
   - Explicit wallet address in the curl quick-start

3. **README.md** — updated to match: Python example, conformance info, full wallet address.

4. **Fixed oracle L11** — resource count expected 3 (pre-web-search) now 4. All 16
   oracles pass.

### Verification

- Server restarted, landing page serves correct HTML
- `rai-par --urls` confirms all 4 subdomains respond 200 on x402 manifest
- All 4 endpoints return 402 with complete challenge (per-endpoint subdomain, body
  challenge, bazaar input schema)
- All 16 ledger oracles pass (L0-L12 including L11_v2)

### What's pending

- **x402-discovery-index listing**: issue JSON prepared but NOT submitted (no GitHub
  credentials). Blocks a listing in the main x402 directory.
- **x402-list.com submission**: pending human review.
- **x402info.com/ecosystem submission**: pending human review.
- **agent402.tools**: registered, pending crawl.

### Money

- Treasury: 29.9998 XNO
- Calls: 0 (no outside buyers yet)
- Payers: 0