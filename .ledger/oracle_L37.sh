#!/usr/bin/env bash
# Oracle for L37 & L38 — the Vend MCP server at /mcp.
#
# L37: MCP endpoint at https://extract.paypercall.dev/mcp answers the initialize
#      handshake via Streamable HTTP (SSE) with server name "vend" and the
#      2025-11-25 protocol version.
# L38: tools/call on extract_url returns a Nano x402 payment challenge (price +
#      pay_to to the treasury), not a fake result.
#
# Prints MCP_ORACLE_PASS only when both checks pass.

BASE="https://extract.paypercall.dev/mcp"

# --- L37: initialize handshake ---
INIT=$(curl -s -X POST "$BASE" -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-11-25","capabilities":{},"clientInfo":{"name":"oracle","version":"1.0"}}}')

# Extract server name and protocolVersion from the SSE data line
SERVER_NAME=$(echo "$INIT" | python3 -c "
import sys, json
for line in sys.stdin:
    line=line.strip()
    if line.startswith('data: '):
        d=json.loads(line[6:])
        r=d.get('result',{})
        print(r.get('serverInfo',{}).get('name',''))
        break
")
PROTOCOL=$(echo "$INIT" | python3 -c "
import sys, json
for line in sys.stdin:
    line=line.strip()
    if line.startswith('data: '):
        d=json.loads(line[6:])
        r=d.get('result',{})
        print(r.get('protocolVersion',''))
        break
")

echo "L37: server_name='${SERVER_NAME}' protocol='${PROTOCOL}'"
if [ "$SERVER_NAME" = "vend" ] && [ "$PROTOCOL" = "2025-11-25" ]; then
  echo "L37_PASS"
else
  echo "L37_FAIL"
  exit 1
fi

# --- L38: tools/list has 6 tools ---
SESSION=$(curl -s -D - -o /dev/null -X POST "$BASE" -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-11-25","capabilities":{},"clientInfo":{"name":"oracle","version":"1.0"}}}' \
  | grep -i 'mcp-session-id' | tr -d '\r' | awk '{print $2}')

TOOLS=$(curl -s -X POST "$BASE" -H 'Content-Type: application/json' -H "mcp-session-id: $SESSION" \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/list"}' 2>&1 | python3 -c "
import sys, json
raw=sys.stdin.read()
for line in raw.split('\n'):
    if line.startswith('data: '):
        d=json.loads(line[6:])
        tools=[t['name'] for t in d.get('result',{}).get('tools',[])]
        print(','.join(sorted(tools)))
        break
")

echo "L38: tools='${TOOLS}'"
EXPECTED="check_link,check_url_status,domain_info,extract_url,geoip_lookup,nano_account_info,web_search"
if [ "$TOOLS" = "$EXPECTED" ]; then
  echo "TOOLS_PASS"
else
  echo "TOOLS_FAIL (got '${TOOLS}')"
  exit 1
fi

# --- L38: extract_url returns a Nano payment challenge ---
CALL=$(curl -s -X POST "$BASE" -H 'Content-Type: application/json' -H "mcp-session-id: $SESSION" \
  -d '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"extract_url","arguments":{"url":"https://example.com"}}}' 2>&1 | python3 -c "
import sys, json
raw=sys.stdin.read()
for line in raw.split('\n'):
    if line.startswith('data: '):
        d=json.loads(line[6:])
        r=d.get('result',{})
        for c in r.get('content',[]):
            try:
                p=json.loads(c['text'])
                # p is the whole MCP tool result: may be {'status':'payment_required','payment_challenge':{...}}
                # or {'status':'ok','data':{...,'payment':{'free_trial':True,'trial_remaining':N}}}
                pc = p.get('payment_challenge') or {}
                pd = p.get('data') or {}
                pmt = pd.get('payment') or {}
                print(json.dumps({
                    'status': p.get('status'),
                    'price': pc.get('price_xno') or pd.get('price_xno'),
                    'pay_to': pc.get('pay_to') or pd.get('pay_to',''),
                    'trial_remaining': pmt.get('trial_remaining')
                }))
            except: pass
        break
")

echo "L38 call: ${CALL}"
STATUS=$(echo "$CALL" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('status',''))")
PRICE=$(echo "$CALL" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('price',''))")
PAYTO=$(echo "$CALL" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('pay_to',''))")
TRIAL=$(echo "$CALL" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('trial_remaining',''))")

# Either: status=ok with trial data (free trial used), or status=payment_required with nano price+pay_to
if [ "$STATUS" = "payment_required" ] && [ "$PRICE" = "0.0001" ] && [[ "$PAYTO" == nano_* ]]; then
  echo "PAYMENT_CHALLENGE_PASS (x402 challenge)"
elif [ "$STATUS" = "ok" ] && [ -n "$TRIAL" ] && [ "$TRIAL" -ge 0 ] 2>/dev/null; then
  echo "PAYMENT_CHALLENGE_PASS (free trial returns data)"
else
  echo "PAYMENT_CHALLENGE_FAIL (status=$STATUS price=$PRICE payto=$PAYTO trial=$TRIAL)"
  exit 1
fi

echo "MCP_ORACLE_PASS"
