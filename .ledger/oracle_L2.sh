#!/usr/bin/env bash
# Oracle for L2: Discovery endpoints return correctly.
set -euo pipefail

HOST="${VEND_TEST_HOST:-localhost}"
PORT="${VEND_TEST_PORT:-8402}"
BASE="http://${HOST}:${PORT}"

# Test /.well-known/x402
x402_status=$(curl -s -o /dev/null -w "%{http_code}" "${BASE}/.well-known/x402")
x402_body=$(curl -s "${BASE}/.well-known/x402")
x402_kind=$(echo "$x402_body" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('kind','missing'))" 2>/dev/null)
x402_resources=$(echo "$x402_body" | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d.get('resources',[])))" 2>/dev/null)

echo "x402_status=${x402_status} kind=${x402_kind} resources=${x402_resources}"

# Test /.well-known/agent-tools.json
at_status=$(curl -s -o /dev/null -w "%{http_code}" "${BASE}/.well-known/agent-tools.json")
at_body=$(curl -s "${BASE}/.well-known/agent-tools.json")
at_name=$(echo "$at_body" | python3 -c "import sys,json; d=json.load(sys.stdin); print('name' in d)" 2>/dev/null)
at_resources=$(echo "$at_body" | python3 -c "import sys,json; d=json.load(sys.stdin); p=d.get('x402',{}); print(len(p.get('resources',[])))" 2>/dev/null)

echo "at_status=${at_status} has_name=${at_name} resources=${at_resources}"

# Verify
if [ "$x402_status" = "200" ] && [ "$x402_kind" = "resource-server" ] && [ "$x402_resources" -ge 1 ] \
   && [ "$at_status" = "200" ] && [ "$at_name" = "True" ] && [ "$at_resources" -ge 1 ]; then
    echo "L2_DISCOVERY_PASS"
    exit 0
else
    echo "L2_DISCOVERY_FAIL"
    exit 1
fi