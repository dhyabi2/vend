# Nano-to-USDC conversion proxy — feasibility report
## Part of corrective action #1

### Problem
4 directories (satring.com, minia2a.uk, x402 Service Encyclopedia, Ontario Protocol)
require USDC on EVM chains for listing fees or registration signatures. Vend's
treasury holds Nano (XNO) only.

### Investigated paths

1. **ChangeNOW API** — No XNO-to-USDC pair available. ChangeNOW's /api/v1/currencies
   does not list XNO as an active currency (returns pair_is_inactive).

2. **SimpleSwap** — Requires API key for /v1/get_pairs. XNO-to-USDC page exists
   on their web frontend but API access is key-gated.

3. **Changelly** — XNO-to-USDC page exists (changelly.com/exchange/xno/usdc) but
   API requires API key authentication.

4. **StealthEX** — API requires API key (returns Auth error without one).

5. **Godex.io** — API endpoints unreachable from this host.

### Blocked by
- **All swap APIs require an API key** — rai-access shows 0 granted keys.
- No EVM wallet on this box to receive USDC or sign EIP-191/EIP-712 messages.
- Even with a key, the conversion proxy would need to be a hosted endpoint
  that accepts Nano, swaps to USDC, and dispenses or holds USDC. This is
  a non-trivial multi-block build with real counterparty risk if it holds funds.

### Alternative paths explored

1. **GitHub issues route** for x402-wiki (free, no USDC needed) — blocked by no
   ACCESS_GITHUB_TOKEN.
2. **x402.eco PR** for client-integrations listing — blocked by no GitHub token.
3. **gold-402 PR** — blocked by no GitHub token.
4. **402index.io** — free but XNO not in known asset list (protocol gap).

### Honest recommendation
The conversion proxy is blocked by API key availability, not by code. A human
would need to:
1. Register for a ChangeNOW/Changelly API key
2. Set up an EVM wallet with Base USDC (~$2-3 for fees)
3. Grant the API key via rai-access

Until then, the four USDC-only directories remain blocked. The correct action
item for a future run once keys are granted is documented in this report.

### What was done instead
- Built and deployed the directory aggregator index (vend-directories.json)
  documenting all 19 directory surfaces including which are blocked by USDC.
- Built dynamic probe script to verify listing health.
- Updated landing page with SEO metadata and directory listing status table.