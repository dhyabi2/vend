#!/usr/bin/env bash
# Oracle for L25: the agent.json discovery manifest answers over public TLS with
# the fields a directory or agent reads first.
set -uo pipefail
echo "AGENTJSON_ORACLE_START"
body=$(curl -s --max-time 20 https://extract.paypercall.dev/.well-known/agent.json)
if [ -z "$body" ]; then
  echo "  FAIL: no response from agent.json"
  echo "AGENTJSON_ORACLE_FAIL"
  exit 1
fi
if printf '%s' "$body" | python3 -c '
import sys, json
d = json.load(sys.stdin)
version = d.get("version")
network = (d.get("x402") or {}).get("network")
payout = str(d.get("payout_address") or "")
assert version == "1.0", "version=" + repr(version)
assert network == "nano:mainnet", "network=" + repr(network)
assert payout.startswith("nano_"), "payout_address=" + repr(payout)
assert d.get("origin"), "origin missing"
print("  PASS: version 1.0, origin " + str(d["origin"]) + ", x402 network nano:mainnet, nano_ payout address")
'; then
  echo "AGENTJSON_ORACLE_PASS"
else
  echo "AGENTJSON_ORACLE_FAIL"
  exit 1
fi
