#!/usr/bin/env bash
# L44 oracle: a health report may not be green while the payment store is unreadable.
#
# Origin: on 2026-09-19 the live server answered 500 on every paid call
# (sqlite3.OperationalError: unable to open database file) while /health said
# `status: ok`. The health endpoint probed upstreams and modules but never its
# own store, so a green light hid a red rail.
set -uo pipefail
cd /root/vend

W=$(mktemp -d)
trap 'rm -rf "$W"' EXIT
fail() { echo "FAIL: $1"; exit 1; }

# 1. the store probe exists and reports on a healthy store
.venv/bin/python3 - <<'PY' || exit 1
import sys
sys.path.insert(0, "/root/vend")
import store_health
ok, detail = store_health.check()
if not ok:
    print(f"FAIL: store_health.check() says unhealthy on a working store: {detail}")
    raise SystemExit(1)
print(f"PASS: healthy store reported ok ({detail})")
PY

# 2. an unreadable store must be reported AS unreadable (not silently ok)
.venv/bin/python3 - "$W" <<'PY' || exit 1
import os, sys, shutil, importlib
W = sys.argv[1]
sys.path.insert(0, "/root/vend")
import store_health
# point the module at a path whose parent is a file, so sqlite cannot create it
blocked = os.path.join(W, "blocked-file")
open(blocked, "w").close()
os.environ["VEND_DB"] = os.path.join(blocked, "vend.sqlite3")
importlib.reload(store_health)
ok, detail = store_health.check()
if ok:
    print("FAIL: an unopenable store was reported healthy")
    raise SystemExit(1)
if "error" not in detail.lower() and "unable" not in detail.lower():
    print(f"FAIL: unhealthy store detail does not explain why: {detail!r}")
    raise SystemExit(1)
print(f"PASS: unopenable store reported unhealthy ({detail})")
PY

# 3. /health wires that probe in: the field must exist and the status must be a
#    function of it, not a constant
.venv/bin/python3 - <<'PY' || exit 1
import re, sys
src = open("/root/vend/server.py").read()
if "store_health" not in src:
    print("FAIL: server.py never consults store_health"); raise SystemExit(1)
matches = re.findall(r'"status":\s*(.+?),?\n', src)
exprs = [m for m in matches if "store_ok" in m or "store" in m]
if not exprs:
    if '"status": "ok",' in src:
        print('FAIL: /health status is still a constant "ok" — it cannot report a store failure')
    else:
        print("FAIL: /health status does not account for the store (looked for a store_ok expression)")
    raise SystemExit(1)
expr = exprs[0]
print(f"PASS: /health status is computed from the store: {expr.strip()}")
PY

echo "L44_STORE_HEALTH_PASS"