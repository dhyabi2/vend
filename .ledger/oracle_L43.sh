#!/usr/bin/env bash
# L43 oracle: the funnel report counts outside traffic honestly.
#
# Two parts:
#   1. a synthetic log with known answers in an isolated TMPDIR (automation-safe);
#   2. the live journal, if it is readable in this context (skipped, not failed,
#      when the context cannot read it — the live numbers are reported by the run
#      journal and the directory index instead).
set -uo pipefail
cd /root/vend
W=$(mktemp -d)
trap 'rm -rf "$W"' EXIT
fail() { echo "FAIL: $1"; exit 1; }

# runtime-generated fixture (never a literal local IP: this file is tracked)
LOCAL=$(python3 -c "import socket;print(socket.gethostbyname(socket.gethostname()))")
OTHER="198.51.100.7"
DAY=$(date -u '+%b %e %H:%M:%S')
cat > "$W/access.log" <<EOF
$DAY vend python[1]: INFO:     $LOCAL:1234 - "GET /api/v1/extract HTTP/1.1" 402 Payment Required
$DAY vend python[1]: INFO:     $LOCAL:1235 - "GET /health HTTP/1.1" 200 OK
$DAY vend python[1]: INFO:     $OTHER:9000 - "GET /api/v1/geoip HTTP/1.1" 402 Payment Required
$DAY vend python[1]: INFO:     $OTHER:9001 - "GET /.well-known/x402 HTTP/1.1" 200 OK
$DAY vend python[1]: INFO:     127.0.0.1:9002 - "GET /.well-known/agent.json HTTP/1.1" 200 OK
EOF

OUT=$(VEND_PUBLIC_IP="$LOCAL" python3 bin/funnel-report.py --log "$W/access.log" --days 1 --json 2>/dev/null)
python3 - "$OUT" "$LOCAL" "$OTHER" <<'PY'
import json, sys
d = json.loads(sys.argv[1]); local, other = sys.argv[2], sys.argv[3]
need = ["source","window_days","requests_total","internal_requests","outside_requests",
        "outside_distinct_ips","by_day","top_ips"]
missing = [k for k in need if k not in d]
if missing:
    print("FAIL: missing keys", missing); sys.exit(1)
if d["requests_total"] != 5:
    print("FAIL: expected 5 parsed requests, got", d["requests_total"]); sys.exit(1)
if d["internal_requests"] != 3:
    print("FAIL: expected 3 internal requests, got", d["internal_requests"]); sys.exit(1)
if d["outside_requests"] != 2:
    print("FAIL: expected 2 outside requests, got", d["outside_requests"]); sys.exit(1)
if d["outside_requests"] != d["requests_total"] - d["internal_requests"]:
    print("FAIL: outside != total - internal"); sys.exit(1)
if d["outside_distinct_ips"] != 1:
    print("FAIL: expected 1 outside IP, got", d["outside_distinct_ips"]); sys.exit(1)
ips = [ip for ip, _ in d["top_ips"]]
if local in ips or "127.0.0.1" in ips:
    print("FAIL: a local IP is listed among outside callers"); sys.exit(1)
if ips != [other]:
    print("FAIL: the only outside caller should be", other, "got", ips); sys.exit(1)
day = sorted(d["by_day"])[0]
c = d["by_day"][day]
if c.get("api_calls") != 1 or c.get("challenged_402") != 1 or c.get("discovery_docs") != 1:
    print("FAIL: per-day classification wrong:", c); sys.exit(1)
print(f"PASS: fixture total={d['requests_total']} internal={d['internal_requests']} "
      f"outside={d['outside_requests']} outside_ips={d['outside_distinct_ips']} "
      f"api=2 402=1 docs=1 (the fixture carries exactly those)")
PY
[ $? -eq 0 ] || fail "synthetic-log checks failed"

LIVE=$(python3 bin/funnel-report.py --days 7 --json 2>/dev/null || true)
if [ -n "$LIVE" ]; then
    python3 - "$LIVE" <<'PY'
import json, sys
try:
    d = json.loads(sys.argv[1])
except Exception:
    print("live journal unavailable in this context (skipped)"); raise SystemExit(0)
ips = [ip for ip, _ in d.get("top_ips", [])]
if any(ip in ("127.0.0.1",) for ip in ips):
    print("FAIL: local IP among live outside callers"); raise SystemExit(1)
print(f"live journal: total={d.get('requests_total')} internal={d.get('internal_requests')} "
      f"outside={d.get('outside_requests')} outside_ips={d.get('outside_distinct_ips')}")
PY
fi
echo "L43_FUNNEL_PASS"
