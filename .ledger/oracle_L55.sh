#!/usr/bin/env bash
# Oracle L55 — OpenAPI discovery manifest lists all 8 paid API endpoints.
#
# Law: "The OpenAPI manifest built from endpoint_meta lists all 8 paid API
# endpoints, including /api/v1/youtube-transcript, each with x-payment-info
# and a declared 402 response."
# Scope: endpoint_meta.py
# Test: build_openapi_spec from a representative bases/prices dict must return
# 8 /api/v1/ paths, each with x-payment-info.price and a 402 response.
set -uo pipefail
cd /root/vend
FAIL=0

python3 - <<'PY' || FAIL=1
import os, sys
sys.path.insert(0, "/root/vend")
import endpoint_meta as em

bases = {
    "extract": "https://extract.paypercall.dev",
    "check": "https://check.paypercall.dev",
    "domain": "https://domain.paypercall.dev",
    "search": "https://search.paypercall.dev",
    "geoip": "https://geoip.paypercall.dev",
    "nano": "https://extract.paypercall.dev",
    "youtube": "https://extract.paypercall.dev",
}
prices = {
    "extract": 0.0001, "domain": 0.0005, "websearch": 0.0001,
    "geoip": 0.0001, "nano": 0.0005, "youtube": 0.0005,
}
spec = em.build_openapi_spec(bases, prices)

api_paths = sorted(p for p in spec["paths"].keys() if "/api/" in p)
EXPECTED = sorted([
    "/api/v1/extract",
    "/api/v1/check-link",
    "/api/v1/domain-info",
    "/api/v1/web-search",
    "/api/v1/geoip",
    "/api/v1/status",
    "/api/v1/nano-info",
    "/api/v1/youtube-transcript",
])
if api_paths != EXPECTED:
    print(f"FAIL: expected {len(EXPECTED)} API paths, got {len(api_paths)}")
    print("  got:", api_paths)
    sys.exit(1)
print("PASS: all 8 API paths present in OpenAPI spec")

# Every paid path must have x-payment-info.price and a 402 response
for p in EXPECTED:
    op = spec["paths"][p]["get"]
    if "x-payment-info" not in op or "price" not in op["x-payment-info"]:
        print(f"FAIL: {p} lacks x-payment-info.price")
        sys.exit(1)
    if "402" not in op.get("responses", {}):
        print(f"FAIL: {p} lacks a declared 402 response")
        sys.exit(1)
print("PASS: all 8 paid paths carry x-payment-info.price and a 402 response")

# youtube-transcript must have url + language params
yt = spec["paths"]["/api/v1/youtube-transcript"]["get"]
params = [x["name"] for x in yt.get("parameters", [])]
if "url" not in params or "language" not in params:
    print(f"FAIL: youtube-transcript params are {params}, expected url+language")
    sys.exit(1)
print("PASS: youtube-transcript declares url and language query params")

# Server.py must pass the youtube base and price to the builder
src = open("server.py").read()
import re as _re
if not _re.search(r'"youtube":\s*(EXTRACT_BASE|PRICE_YT_XNO)', src):
    print("FAIL: server.py openapi_spec() does not pass youtube base/price")
    sys.exit(1)
print("PASS: server.py passes youtube base/price to build_openapi_spec")
PY

[ $FAIL -eq 0 ] && echo "L55_PASS" || echo "L55_FAIL"
exit $FAIL
