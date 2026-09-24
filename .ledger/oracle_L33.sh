#!/usr/bin/env bash
# Oracle L33: Enhanced health endpoint returns upstreams with status and timing.
set -euo pipefail
cd "$(dirname "$0")/.."

echo "=== L33: Enhanced health check ==="

# Start server on a private port with a temp DB
TEMP_DB=$(mktemp /tmp/vend-test-XXXXXX.db)
TEMP_PORT=$(( ((RANDOM << 10) | RANDOM) % 10000 + 20000 ))

cleanup() { rm -f "$TEMP_DB"; }
trap cleanup EXIT

VEND_DB="$TEMP_DB" VEND_PORT="$TEMP_PORT" \
    .venv/bin/python server.py &
SERVER_PID=$!

# Wait for server
for i in $(seq 1 15); do
    if curl -sf "http://127.0.0.1:$TEMP_PORT/health" > /dev/null 2>&1; then
        break
    fi
    sleep 0.3
done

# Fetch health endpoint
HEALTH=$(curl -sf "http://127.0.0.1:$TEMP_PORT/health" 2>/dev/null || echo '{"error":"unreachable"}')
kill "$SERVER_PID" 2>/dev/null || true
wait "$SERVER_PID" 2>/dev/null || true

echo "health response: $HEALTH"

# Check it has upstreams with status and response_time_ms
echo "$HEALTH" | python3 -c "
import json,sys
d=json.load(sys.stdin)
u=d.get('upstreams',{})
if not isinstance(u,dict):
    print(f'FAIL: upstreams missing or not a dict: {u!r}')
    sys.exit(1)
for name in ('rpc','ipapi','search'):
    entry=u.get(name)
    if not isinstance(entry,dict):
        print(f'FAIL: {name} upstream missing or not a dict')
        sys.exit(1)
    if 'status' not in entry:
        print(f'FAIL: {name} has no status key')
        sys.exit(1)
    if 'response_time_ms' not in entry:
        print(f'FAIL: {name} has no response_time_ms key')
        sys.exit(1)
    print(f'OK: {name} status={entry[\"status\"]} time={entry[\"response_time_ms\"]}ms')
rf=d.get('recoverable_failures',None)
if rf is None:
    print(f'FAIL: recoverable_failures missing')
    sys.exit(1)
print(f'OK: recoverable_failures={rf}')
print('L33_HEALTH_PASS')
"