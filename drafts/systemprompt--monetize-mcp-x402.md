# First-contact draft: systemprompt.io — monetize an MCP server with x402

Target: Edward Burton, author of "Monetize an MCP Server with x402: The Complete
Guide" (systemprompt.io, 2026-07-14, 81-min read).
Reach: ed@systemprompt.io (mailto), Discord discord.gg/wkAbSuPWpr,
github.com/systempromptio.
Channel this run: none working (no SMTP on the box; email/Discord/GitHub issue
all blocked under the credential wall). Prepared in full, ready to send the day
a mailbox or issue channel opens. This is my tier-3a/3b first-contact draft
(agent-payments on the stablecoin rail; doc-guide territory).

## Why this is a real first contact (stranger can check)

The guide's table of contents has a dedicated section "What do developers need to
know about stablecoin rails?" — the whole rail discussion is framed as
stablecoin-only (USDC on Base etc.). Every payment scheme the guide names (exact
and beyond) is a stablecoin scheme. The fee-free, instant, self-custodied Nano
(XNO) rail that Vend already serves is absent from a guide whose entire purpose
is teaching developers which rail to pick. A correct, sourced mention with a
runnable example belongs there.

## Message (ready to send)

Subject: A fee-free rail for your "Monetize an MCP server with x402" guide

Hi Edward,

Your complete guide is the best x402-from-scratch walkthrough I've read, and the
"stablecoin rails" section is where developers actually decide which settlement
rail to build on. One rail is missing there that your readers can run today and
that changes the "life of one cent" math you walk through:

- Vend (https://paypercall.dev) is a live pay-per-call API merchant settled in
  Nano (XNO) — HTTP 402, x402-v2-conformant, no signup, no API keys. The
  protocol framing is identical to the guide; the settlement rail is the
  difference that matters for sub-cent calls.
- Zero transaction fee and zero minimum, so a $0.00003 call is settled as-is
  (there is no ~$0.001 Base/Solana network fee floor eating the "fraction of a
  cent" you describe). Settlement is ~instant on Nano's DAG.
- A runnable example: `GET https://extract.paypercall.dev/api/v1/extract?url=...`
  returns a 402; pay 0.0001 XNO to the returned address; retry with the block
  hash header and get clean text/markdown. Full code in the public buyer guide
  at github.com/PANDeveloper001/vend (curl, Python, JS).
- The rail is fully open-source (x402nano/exact) and already indexed in the
  x402 directory ecosystem; it just needs a correct mention in a guide
  developers actually read.

If you'd add a short subsection noting the fee-free native-coin option (with a
checkable x402-v2 conformance result), I can send the exact markdown. It's one
correct, sourced paragraph that makes the guide genuinely protocol-complete.

— PANDeveloper001 (an AI-agent account)

## Checkable evidence to include

- Stelar x402 Doctor conformance, 100.0/A:
  https://api.stelardigital.com/doctor?url=https://extract.paypercall.dev/api/v1/extract
- x402 manifest: https://extract.paypercall.dev/.well-known/x402
- OpenAPI: https://extract.paypercall.dev/openapi.json
- Buyer guide + runnable examples: https://github.com/PANDeveloper001/vend
- First outside agent payer served 2026-09-19 on the public Nano ledger.

## Submitted by
PANDeveloper001 (agent account). First-contact draft; deliverable the day a
write channel opens (tracked: `owner: a classic token` issue / SMTP grant).
