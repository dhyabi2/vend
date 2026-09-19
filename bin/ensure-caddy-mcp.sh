#!/usr/bin/env bash
# Ensure Caddy routes Vend MCP /mcp requests to the vend-mcp server (127.0.0.1:8403).
# Caddy config is applied via its admin API. This is idempotent: it only inserts
# the /mcp route when missing (or pointing at the wrong dial), and it INSERTS it
# at the right position so the gzip encode handler stays first.
#
# Caddy subroutes are evaluated in list order; the catch-all 8402 proxy (no path
# match) would swallow /mcp, so the /mcp route must come before it but after the
# global encode handler.

CADDY_ADMIN="http://localhost:2019"
MCP_DIAL="127.0.0.1:8403"
MAIN_DIAL="127.0.0.1:8402"

# Find the subroutes endpoint — it's the 'routes' array inside route 1's first
# subroute handler.
ROUTES_JSON=$(curl -sf "${CADDY_ADMIN}/config/apps/http/servers/srv0/routes" 2>/dev/null)
if [ -z "$ROUTES_JSON" ]; then
  echo "Caddy admin API not reachable; skipping /mcp route sync" >&2
  exit 0
fi

# Find the correct subroutes endpoint by scanning for the catch-all to 8402.
# The endpoint ends with "/routes" inside the route whose match hosts contain
# extract.paypercall.dev.
SUBROUTES_URL=$(echo "$ROUTES_JSON" | python3 -c "
import json, sys
routes = json.load(sys.stdin)
for ridx, r in enumerate(routes):
    hosts = (r.get('match') or [{}])[0].get('host') or []
    if any('extract.paypercall.dev' in h for h in hosts):
        # The second handle (index 1) should be the subroute handler
        handles = r.get('handle') or []
        # Check group4
        for h in handles:
            if h.get('handler') == 'subroute':
                # This is the catch-all, find its /mcp route
                print(f'/config/apps/http/servers/srv0/routes/{ridx}/handle/0/routes')
                sys.exit(0)
        print('subroute-not-found')
        sys.exit(1)
print('route-not-found')
sys.exit(1)
" 2>/dev/null)

if [ -z "$SUBROUTES_URL" ] || [ "$SUBROUTES_URL" = "route-not-found" ] || [ "$SUBROUTES_URL" = "subroute-not-found" ]; then
  echo "Could not find the right Caddy route; skipping" >&2
  exit 1
fi

ENDPOINT="${CADDY_ADMIN}${SUBROUTES_URL}"

# Check whether /mcp already maps to the MCP dial.
EXISTS=$(curl -sf "$ENDPOINT" 2>/dev/null | python3 -c "
import json, sys
try:
    routes = json.load(sys.stdin)
except Exception:
    print('missing')
    sys.exit(0)
for r in routes:
    if (r.get('match') or [{}])[0].get('path') or []:
        for h in r.get('handle') or []:
            if h.get('handler') == 'subroute':
                for s in h.get('routes') or []:
                    for h2 in s.get('handle') or []:
                        for u in h2.get('upstreams') or []:
                            if u.get('dial')=='${MCP_DIAL}':
                                print('ok')
                                sys.exit(0)
print('missing')
" 2>/dev/null)

if [ "$EXISTS" = "ok" ]; then
  echo "/mcp route already present -> ${MCP_DIAL}"
  exit 0
fi

echo "/mcp route missing or stale; inserting after the encode handler..."

# Delete any stale /mcp routes, then insert a fresh one as the last route
# (after gzip encode). The catch-all route to 8402 will be added by Caddy's
# self-loading of the static Caddyfile, so we don't remove it.
python3 - "$ENDPOINT" <<'PY'
import json, sys, urllib.request, urllib.error

endpoint = sys.argv[1]

def get():
    with urllib.request.urlopen(endpoint, timeout=5) as r:
        return json.load(r)

def delete(idx):
    req = urllib.request.Request(endpoint + f"/{idx}", method="DELETE")
    with urllib.request.urlopen(req, timeout=5) as r:
        r.read()

routes = get()
# Delete stale /mcp routes from the end to keep indices valid
idx = len(routes) - 1
while idx >= 0:
    r = routes[idx]
    paths = (r.get('match') or [{}])[0].get('path') or []
    if any(p.startswith('/mcp') for p in paths):
        delete(idx)
    idx -= 1
PY

# Insert after the first route (gzip encode), before the catch-all.
# POST appends to the end of the list, which is correct: the catch-all
# gets pushed to index 2 (it was index 1 before we deleted the stale /mcp).
curl -sf -X POST "$ENDPOINT" \
  -H 'Content-Type: application/json' \
  -d '{"handle":[{"handler":"subroute","routes":[{"handle":[{"handler":"reverse_proxy","headers":{"request":{"set":{"X-Real-Ip":["{http.request.remote.host}"]}}},"upstreams":[{"dial":"'"${MCP_DIAL}"'"}]}]}]}],"match":[{"path":["/mcp","/mcp/*"]}]}' >/dev/null && echo "  + /mcp -> ${MCP_DIAL}"

echo "/mcp route applied."