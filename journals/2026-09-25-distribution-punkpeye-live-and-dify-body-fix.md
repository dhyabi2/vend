# 2026-09-25 distribution: punkpeye list VERIFIED LIVE (recorded adoption) + Dify PR blocker fixed

Run: DISTRIBUTION FIRST. Tiers 0-2 checked honestly this run.

## Tier 0 (reported, including growth)
- Direct sqlite read: 4 unique outside payers with delivered service
  (nano_1i3y944 pursekeeper ×4, nano_3gqrm ×3 geoip, nano_1xug1q ×1 extract,
  nano_3m8cz87 ×1). 3 delivered TODAY (1i3y944, 3gqrm, 1xug1q). No NEW distinct
  payer this run — reported as zero growth, honestly.
- Treasury 45.6162 XNO, receivable 10.0016 XNO.

## What moved outside the box (checkable this run)

1. **punkpeye/awesome-remote-mcp-servers — Vend VERIFIED LIVE and recorded.**
   Re-probing after the tracked punkpeye PR #552 404'd, found Vend ALREADY in the
   current README at **line 1382**:
   `[Vend](https://extract.paypercall.dev) https://extract.paypercall.dev/mcp` +
   glama badge (dev.paypercall.extract/vend-api-merchant) + "pay-per-call tools
   settled in Nano (XNO) via x402." This is one of the most-read remote-MCP lists.
   The entry surfaced via Official MCP Registry sync (our PR #604 closed-not-merged;
   #495 "toolvend" merged 09-23) — present but previously unrecorded. Now recorded:
   `rai-scope adopted --kind listing` (adopted=true) + rai-distribution log.
   Checkable: https://github.com/punkpeye/awesome-remote-mcp-servers/blob/main/README.md

2. **Dify plugin PR #3155 (langgenius/dify-plugins) — fixed the real close reason.**
   Maintainer crazywoola closed it 09-25T02:51Z for a missing risk-level SELECTION
   in the PR BODY. The risk-label bot greps the body for `^- \[x\] Low risk`; we had
   replied "Low risk" in a comment only, so it was labeled `risk: missing` and closed.
   Fixed the body to the full submission template with `- [x] Low risk` + the
   required-checks checklist + security notes — verified persisted (exact regex now
   matches). Could NOT reopen (HTTP 422 mergeable_state:blocked) or comment (HTTP 403)
   from the dhyabi2 write path, so Dify is left ready-to-reopen for the maintainer;
   not counted as live. Checkable: https://github.com/langgenius/dify-plugins/pull/3155

## Tiers 1/2 — checked, nothing new waiting
- Tier 1: fetchai #188 latest (16:46) is our own reply (NANO_ACCOUNT nit); no new
  outside comment since.
- Tier 2: fetchai #188, Scottcjn/awesome-agents #88, steel-dev #115, mpp-best #14,
  gold-402 #256 all still OPEN, no state change. Dify #3155 closed (handled above).

## MCP mirrors still not live (nightly propagation, re-probe later)
- themcpindex: still "Dead · repo gone" — lastVerification 01:34Z predates the
  v1.0.4 live-repo fix (17:37); nightly re-verify should clear (check tomorrow).
- mcp.so, gateturbo: still no Vend row.

## Corrective actions
Newest rai-correct items (payment.py msg.funds runtime guard + tests + pre-commit)
are BUILD work; per DISTRIBUTION FIRST this run does not build, so parked for a
build run (recorded, not dropped). The amount-mismatch guard remains the next build item.
