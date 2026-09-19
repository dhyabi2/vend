# Run: Adoption verification sweep and pursekeeper discovery

## Accomplishments

1. **pursekeeper.dev discovery**: Vend API Merchant is now auto-listed on the Nano x402 directory at `pursekeeper.dev/sellers` — a third-party, AI-agent-run directory of services that take Nano, verified by payment. The `/sellers` page lists Vend with full endpoint descriptions, prices, and x402 manifest documentation. The landscape journal (`/landscape`) also names Vend extensively. This happened through pursekeeper's automated Nano ecosystem scanning, not through our submission. The listing criteria: (a) 402 answers naming nano:mainnet, (b) one paid call completes (landscape says "Listed as seller 12 after one paid call"), (c) stays up.

2. **Concurrent re-verification of 12 directory listings** via rai-par:
   - **Still live (5/5):** AI Kendra, Vivioo, nohumans.directory, agentstore.tools, AgentBoard (agents-launch)
   - **Still pending (7):** agentndx.ai (200 but generic), theagentrank (404), mcp.directory (404), mcpservers.org (404), aiagenttools.dev (404), Best AI Agents, BotMarket
   - **A2A Registry still live**: 23 "Vend" matches, 34 "paypercall" matches on the dedicated agent page
   - **agent402.tools refreshed**: 7 tools, nano:mainnet, routable=true, health=1

3. **purskeeper x402 feedback**: The listing notes a payment implementation divergence — Vend requires `X-PAYMENT` header with a self-broadcast block hash, while some x402 exact clients expect a different flow. A buyer with a stock x402 exact client cannot pay Vend directly. Product gap noted for a future run.

4. **No new revenue**: Treasury still ~33.3 XNO + 12.3 pending, 1 lifetime payer (unchanged).

## Money

- Balance: 33.3 XNO
- Pending: 12.3 XNO
- 1 lifetime outside payer (geoip, 0.0001 XNO)
- Zero new revenue this run

## Open items

- GitHub push key still open (owner decision pending)
- VEND_USDC_ADDRESS not set (blocks ~10 directories, needed for CDP Bazaar + hybrid rail)
- vend-client PyPI: needs pending trusted publisher + repo visibility
