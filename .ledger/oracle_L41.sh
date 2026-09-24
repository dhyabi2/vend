#!/usr/bin/env bash
# Oracle for L41 & L42 — A2A agent-card.json at /.well-known/agent-card.json.
#
# L41: /.well-known/agent-card.json serves a conformant A2A card naming the six
#      skills and the Nano x402 rail with the treasury payTo.
# L42: The card describes 6 Vend skills with name, description, and the Nano x402
#      payment rail as the sole security scheme.
#
# Prints AGENTCARD_ORACLE_PASS only when both checks pass.

set -uo pipefail
BASE="${VEND_BASE:-http://127.0.0.1:8402}"

fails=""

# Fetch the agent card
CARD=$(curl -sf "$BASE/.well-known/agent-card.json" 2>/dev/null) || {
    echo "AGENTCARD_FAIL: could not fetch /.well-known/agent-card.json"
    exit 1
}

python3 - "$CARD" <<'PY'
import sys, json

card = json.loads(sys.argv[1])
fails = []

# L41: conformant A2A card
for key in ("protocolVersion", "name", "description", "url", "version", "skills"):
    if not card.get(key):
        fails.append(f"L41: missing required field {key!r}")

pv = str(card.get("protocolVersion", ""))
if not pv.startswith("0.3"):
    fails.append(f"L41: protocolVersion={pv!r}, expected 0.3.x")

# L42: six skills with name and description
skills = card.get("skills") or []
ids = {s.get("id") for s in skills if isinstance(s, dict)}
expected = {"extract_url", "check_link", "domain_info", "web_search",
            "geoip_lookup", "nano_account_info"}
missing = expected - ids
if missing:
    fails.append(f"L41: skills missing {sorted(missing)}, got {sorted(ids)}")

for s in skills:
    if not isinstance(s, dict) or not s.get("name") or not s.get("description"):
        fails.append(f"L42: skill {s.get('id')!r} lacks name/description")

# L42: x402-nano as the sole security scheme
scheme = (card.get("securitySchemes") or {}).get("x402-nano") or {}
if scheme.get("type") != "x402":
    fails.append(f"L42: security scheme type is {scheme.get('type')!r}, expected 'x402'")
if scheme.get("network") != "nano:mainnet":
    fails.append(f"L42: security scheme network is {scheme.get('network')!r}, expected nano:mainnet")
payto = scheme.get("payTo", "")
if not payto.startswith("nano_"):
    fails.append(f"L42: security scheme payTo is {payto!r}, expected a nano_ account")
prices = scheme.get("prices") or {}
if prices.get("extract_url") != 0.0001 or prices.get("domain_info") != 0.0005:
    fails.append(f"L42: advertised prices mismatch: {prices}")
required_security = [{"x402-nano": []}]
if card.get("security") != required_security:
    fails.append(f"L42: security requirement is {card.get('security')!r}, expected {required_security}")

# Also check the card exists at /.well-known/agent-card.json (HTTP 200)
if fails:
    print("AGENTCARD_CHECK_FAIL:")
    for f in fails:
        print(f"  - {f}")
    sys.exit(1)

print("L41_PASS: agent-card.json has protocolVersion/name/description/url/version/skills with A2A 0.3.x")
print("L42_PASS: 6 skills with name+description; x402-nano scheme (type=x402, network=nano:mainnet, payTo=nano_, correct prices, sole security requirement)")
print("AGENTCARD_ORACLE_PASS")
PY