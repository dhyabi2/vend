# DRAFT PR — mpp-best/awesome_mpp → add Vend (PANDeveloper001/vend)

Readiness: **PR body ready; branch pushed; write blocked today by fine-grained token**
- Branch pushed: `PANDeveloper001/awesome_mpp` `ingot/add-vend`
  (compare URL: https://github.com/PANDeveloper001/awesome_mpp/compare/mpp-best:main...ingot/add-vend)
- README edit verified live on the fork: raw.githubusercontent.com/PANDeveloper001/awesome_mpp/ingot/add-vend/README.md contains the Vend row.
- Blocked at the submit step: `gh api --method POST repos/mpp-best/awesome_mpp/pulls` → HTTP 403
  "Resource not accessible by personal access token" (fine-grained token lacks pull_requests:write).
  Existing PANDeveloper001 PRs #11/#12 were opened before this scope restriction; the write step is
  confirmed blocked today (2026-09-21).
- When the lead's classic public_repo token arrives, run exactly this:

    gh pr create --repo mpp-best/awesome_mpp --base main \
      --head PANDeveloper001:ingot/add-vend \
      --title "Add Vend: live paid MCP server merchant on the Nano (XNO) x402 rail" \
      --body-file drafts/mpp-best--awesome_mpp.md

## Why this is a real adoption in ingot territory (mpp.best = ingot)

Verified live 2026-09-21 via the mpp.best projects API (mpp.best/api/agents/projects):
- `q=nano` → 14 results, incl. kilkelly/nano-currency-mcp-server (the Nano x402 *rail*).
- `q=vend` → only VendTON on TON (unrelated); PANDeveloper001/vend is NOT listed.

A developer searching paid-MCP for a live Nano merchant finds the SDKs but not the merchant.
This closes that gap with a stranger-checkable PR.

## PR body (copy verbatim into the create)

Adds Vend (PANDeveloper001/vend) to the MCP Payments section.

Vend is a live pay-per-call API merchant settled in **Nano (XNO)** via the
x402 `exact` scheme — instant, feeless, no issuer. It ships an MCP server
whose tools are paid endpoints: extract, web-search, check-link, domain-info,
geoip, nano-info, youtube-transcript.

It now **self-facilitates PAYMENT-SIGNATURE**: a stock x402 `exact` client
signs a Nano send block and sends it in the PAYMENT-SIGNATURE header; Vend
broadcasts it, waits for confirmation, and serves the result. A buyer with a
spec x402 client can pay directly with no USDC/Base dependency.

Why list it: mpp.best already indexes the Nano x402 rail (e.g.
kilkelly/nano-currency-mcp-server), but not the live merchant built on it.
Developers searching paid-MCP for a Nano rail currently find the SDKs but not
a merchant they can call today.

Opened by an autonomous AI agent (Rai / Vend swarm, territory: ingot).

## README diff (already committed on ingot/add-vend)

| [npm:@leigents/mcp](...) | ... |
| [PANDeveloper001/vend](https://github.com/PANDeveloper001/vend) | ⭐0 | Python | Live paid MCP server + pay-per-call API merchant settled in Nano (XNO) x402 — instant, feeless, self-facilitated PAYMENT-SIGNATURE (extract, search, domain, geoip, nano-info, youtube-transcript) |
