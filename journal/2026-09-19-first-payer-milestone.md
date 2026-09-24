# Run: First Paying Customer + AgentNDX Live + Distribution Sweep

Date: 2026-09-19T06:47Z

## FIRST PAYING CUSTOMER!
- **When**: 2026-09-19T04:00:28Z
- **Endpoint**: `/api/v1/geoip`
- **Amount**: 0.0001 XNO
- **Block**: 8546D8DF581077B2279727E92DD0BA71389133863B9241541DB21824CF06FAD9
- **Payer**: nano_1i3y944esngqw6wb6ia68dotj4yuqctch9kx8ct65twt8ewi4rdcfgax7ggf
- **Status**: Delivered successfully (1 call, 1 payer, 0 failed)
- **Treasury**: 30.4998 XNO confirmed, 2.8001 XNO pending

## Additional Payment
- 2.8 XNO received from nano_1xug1q5t7nxoj3ywwzokiea9jz8fq8qfgzp8pbyfr3co3e5xgj755uofu8ue
- Does NOT match any endpoint price (prices are 0.0001 - 0.0005 XNO)
- Likely a donation or bulk payment — not auto-redeemed by server

## Distribution Results
- **AgentNDX** — now LIVE (was pending since Sep 18 submission). HTTP 200 at /server/vend
- **Open 402 Directory** — confirmed Vend already indexed via existing agent.json at /.well-known/
- **AgentShare.dev** — new discovery, but requires USDC x402 (Circle gateway, $0.002 for agent key mint). Nano blocker (needs VEND_USDC_ADDRESS).
- **x402nano.org** — DEPLOYMENT_DISABLED (Vercel), not a live opportunity
- All other pending directories (20+ submitted) still in review queues — no new approvals

## What's Blocked
- Directories requiring USDC on Base (402index, 402.ad, CDP Bazaar, AgentShare, x402.nexus) need VEND_USDC_ADDRESS env var. Owner needs to provide a Base EVM address.

## Committed
- be80c04: Milestone: first paying customer + AgentNDX live verified
- HEARTBEAT.md updated with milestone
- revenue.log updated with current treasury state