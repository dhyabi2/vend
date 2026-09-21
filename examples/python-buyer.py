#!/usr/bin/env python3
"""
Vend API Merchant — x402 Buyer Example (Python)

Demonstrates the three-step x402 payment flow for any Vend endpoint:

  1. Call the endpoint → receive HTTP 402 with payment challenge
  2. Parse the challenge to get the Nano destination and price
  3. Send the Nano payment, then retry with that block's hash

Prerequisites: pip install httpx

Usage:
  python examples/python-buyer.py extract '{"url": "https://example.com"}'
  python examples/python-buyer.py search '{"q": "nano cryptocurrency"}'
  python examples/python-buyer.py domain '{"domain": "example.com"}'
  python examples/python-buyer.py check-link '{"url": "https://example.com"}'
  python examples/python-buyer.py status '{"url": "https://example.com"}'
  python examples/python-buyer.py geoip '{"ip": "8.8.8.8"}'
  python examples/python-buyer.py nano-info '{"account": "nano_3t6k35gi95xu6tergt6p69ck76ogmitsa8mnijtpxm9fkcm736xtoncuohr3"}'
  python examples/python-buyer.py youtube-transcript '{"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"}'
"""

import json
import os
import sys
from urllib.parse import urlencode

import httpx

# --- Configuration (edit these for your environment) ---

# API base per endpoint
# Default Nano payment destination (all payments go here)
VEND_PAY_TO = "nano_1yo6c1t64ahfjdw1dxizmbbnpdmbrckwhw9phbg5pdkeubrizga4qhnjmnx7"

ENDPOINTS = {
    "extract": {
        "url": "https://extract.paypercall.dev/api/v1/extract",
        "price": 0.0001,
    },
    "check-link": {
        "url": "https://check.paypercall.dev/api/v1/check-link",
        "price": 0.0001,
    },
    "status": {
        "url": "https://extract.paypercall.dev/api/v1/status",
        "price": 0.0001,
    },
    "domain": {
        "url": "https://domain.paypercall.dev/api/v1/domain-info",
        "price": 0.0005,
    },
    "search": {
        "url": "https://search.paypercall.dev/api/v1/web-search",
        "price": 0.0001,
    },
    "geoip": {
        "url": "https://geoip.paypercall.dev/api/v1/geoip",
        "price": 0.0001,
    },
    "nano-info": {
        "url": "https://extract.paypercall.dev/api/v1/nano-info",
        "price": 0.0005,
    },
    "youtube-transcript": {
        "url": "https://extract.paypercall.dev/api/v1/youtube-transcript",
        "price": 0.0005,
    },
}

# Path to the feeless402 CLI for sending Nano payments.
# Install: pip install feeless402
# Or use any Nano wallet that lets you send from the command line.
FEELESS_CLI = os.environ.get("FEELESS_CLI", "nano-pay")

# Your Nano wallet seed or private key (for feeless402).
# NEVER hardcode this in a script you share. Use an environment variable.
NANO_WALLET = os.environ.get("NANO_WALLET", "")


# --- Step 1: Call the endpoint (expect 402) ---

def get_402_challenge(endpoint_name: str, params: dict) -> dict:
    """Call a Vend endpoint unpaid and return the x402 challenge."""
    ep = ENDPOINTS[endpoint_name]
    url = ep["url"] + "?" + urlencode(params)

    print(f"\n  Step 1: Calling {endpoint_name} endpoint...")
    print(f"  GET {url}")

    with httpx.Client(timeout=15) as client:
        resp = client.get(url)

    if resp.status_code != 402:
        print(f"  ERROR: Expected 402 but got {resp.status_code}")
        print(f"  Response: {resp.text[:500]}")
        sys.exit(1)

    body = resp.json()
    print(f"  -> HTTP 402: {body.get('message', 'payment required')}")
    print(f"     Price:    {body['price_xno']} XNO")
    print(f"     Pay to:   {body['pay_to'][:15]}...")
    print(f"     Network:  {body['accepts'][0]['network']}")
    print(f"     Asset:    {body['accepts'][0]['asset']}")

    return body


# --- Step 2: Send the Nano payment ---

def send_nano_payment(challenge: dict) -> str:
    """Send the quoted Nano amount and return the block hash."""
    accept = challenge["accepts"][0]
    pay_to = accept["payTo"]
    amount_raw = accept["amount"]  # raw Nano (10^30 raw = 1 XNO)
    price_xno = challenge["price_xno"]

    print(f"\n  Step 2: Sending {price_xno} XNO to {pay_to[:15]}...")

    if NANO_WALLET:
        # Use feeless402 CLI to send
        cmd = f'{FEELESS_CLI} send --to {pay_to} --raw-amount {amount_raw} --wallet "{NANO_WALLET}"'
        print(f"  Running: {FEELESS_CLI} send --to {pay_to[:15]}... --raw-amount {amount_raw[:10]}...")
        import subprocess
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            print(f"  ERROR: Payment failed: {result.stderr[:300]}")
            sys.exit(1)
        block_hash = result.stdout.strip()
    else:
        # Manual mode — print instructions
        print(f"\n  *** MANUAL PAYMENT REQUIRED ***")
        print(f"  Send exactly {price_xno} XNO from your wallet to:")
        print(f"    {pay_to}")
        print(f"\n  Then paste the block hash and press Enter:")
        block_hash = input("  Block hash: ").strip()

    if not block_hash or len(block_hash) != 64:
        print(f"  ERROR: Invalid block hash: '{block_hash}'")
        sys.exit(1)

    print(f"  -> Payment sent. Block: {block_hash[:16]}...")
    return block_hash


# --- Step 3: Retry with the block hash (get the result) ---

def get_paid_result(endpoint_name: str, params: dict, block_hash: str) -> dict:
    """Call the endpoint with the X-PAYMENT header and get the result."""
    ep = ENDPOINTS[endpoint_name]
    url = ep["url"] + "?" + urlencode(params)

    print(f"\n  Step 3: Retrying with payment proof...")

    with httpx.Client(timeout=30) as client:
        resp = client.get(
            url,
            headers={
                "X-PAYMENT": block_hash,
                "User-Agent": "vend-buyer-example/1.0",
            },
        )

    if resp.status_code == 402:
        # Could be already redeemed, insufficient, or invalid
        body = resp.json()
        print(f"  ERROR: Payment rejected: {body.get('error', 'unknown')}")
        print(f"  Message: {body.get('message', '')}")
        if body.get("error") == "payment_already_redeemed":
            print(f"  -> This block hash was already used. Send a new payment.")
        sys.exit(1)

    if resp.status_code != 200:
        print(f"  ERROR: Unexpected status {resp.status_code}")
        print(f"  Response: {resp.text[:500]}")
        sys.exit(1)

    body = resp.json()
    print(f"  -> HTTP 200: Success!")
    print(f"     Receipt:  {body.get('receipt', 'N/A')[:48]}...")
    return body


# --- Main ---

def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    endpoint_name = sys.argv[1]
    params = json.loads(sys.argv[2])

    if endpoint_name not in ENDPOINTS:
        print(f"Unknown endpoint '{endpoint_name}'. Choose from: {', '.join(ENDPOINTS.keys())}")
        sys.exit(1)

    print(f"Vend API Merchant — x402 Buyer Example")
    print(f"{'='*50}")

    # Step 1: Get the 402 challenge
    challenge = get_402_challenge(endpoint_name, params)

    # Step 2: Send the payment
    block_hash = send_nano_payment(challenge)

    # Step 3: Get the paid result
    result = get_paid_result(endpoint_name, params, block_hash)

    print(f"\n{'='*50}")
    print(f"Result ({endpoint_name}):")
    print(json.dumps(result, indent=2, default=str)[:2000])

    print(f"\nDone. {ENDPOINTS[endpoint_name]['price']} XNO spent, 1 result received.")


if __name__ == "__main__":
    main()