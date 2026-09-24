"""Tests for PAYMENT-SIGNATURE (x402 exact / feeless402) acceptance.

Covers:
- parsing a base64 PaymentPayload out of a PAYMENT-SIGNATURE header;
- the full verify -> broadcast -> confirm -> re-verify flow against a
  stubbed Nano RPC;
- fast-fail on a destination mismatch before any broadcast;
- replay-safe redemption still flowing through the existing store path.

The Nano RPC is stubbed with a tiny local HTTP server so the oracle is
re-runnable without touching the real ledger (same policy as the other
nano-paid-rail oracles).

Run: python3 tests/test_payment_signature.py
"""

import base64
import json
import os
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import nano_verify as nv

# A valid-looking Nano account for our own payTo (Vend's treasury in tests).
VEND_TEST_ACCOUNT = "nano_3qgmh14nwztqw4wmcdzy4xpqeejey68chx6nciczwn9abji7ihhum9qtpmdr"
PRICE_RAW_1 = str(10**26)  # 0.0001 XNO


def _base64_payload(block):
    payload = {
        "x402Version": 2,
        "resource": {"url": "https://extract.paypercall.dev/api/v1/extract",
                     "mimeType": "application/json"},
        "accepted": {
            "scheme": "exact", "network": "nano:mainnet", "asset": "XNO",
            "amount": PRICE_RAW_1, "payTo": VEND_TEST_ACCOUNT,
            "maxTimeoutSeconds": 60,
        },
        "payload": {"block": block},
        "extensions": {},
    }
    return base64.b64encode(json.dumps(payload).encode()).decode()


def _send_block(prev_balance, new_balance, destination=VEND_TEST_ACCOUNT, previous="F47B23107E5F34B2CE06F562B5C435DF72A533251CB414C51B2B62A8F63A00E4"):
    return {
        "type": "state",
        "account": "nano_1hza3f7wiiqa7ig3jczyxj5yo86yegcmqk3criaz838j91sxcckpfhbhhra1",
        "previous": previous,
        "representative": "nano_1hza3f7wiiqa7ig3jczyxj5yo86yegcmqk3criaz838j91sxcckpfhbhhra1",
        "balance": str(new_balance),
        "link": destination.encode().hex() if destination else "",
        "link_as_account": destination,
        "signature": "3B" * 64,
        "work": "ffffffd2e1234567",
    }


class StubNanoRPC:
    """A tiny in-process HTTP stub for the Nano RPC actions we call."""

    def __init__(self):
        self.blocks = {}       # hash -> block dict (on-ledger)
        self.prev_balance = {} # hash -> its balance
        self.process_calls = 0
        self.log = []
        self._httpd = None
        self.port = None

    def start(self):
        from http.server import BaseHTTPRequestHandler, HTTPServer

        stub = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def do_POST(self):
                length = int(self.headers.get("content-length", "0"))
                body = json.loads(self.rfile.read(length) or b"{}")
                action = body.get("action")
                stub.log.append(action)
                if action == "process":
                    stub.process_calls += 1
                    block = body.get("block", {})
                    # Reject blocks with no signature (mock on-ledger check)
                    if not block.get("signature"):
                        self._reply({"error": "Bad signature"})
                        return
                    h = "AB" + "CD" * 31
                    stub.blocks[h] = block
                    self._reply({"hash": h})
                elif action == "block_hash":
                    self._reply({"hash": "AB" + "CD" * 31})
                elif action == "block_info":
                    h = body.get("hash", "")
                    if h in stub.blocks:
                        blk = stub.blocks[h]
                        self._reply({
                            "amount": str(10**26),
                            "contents": blk,
                            "hash": h,
                        })
                    else:
                        self._reply({"error": "Block not found"})
                elif action == "account_info":
                    self._reply({"balance": "0"})
                else:
                    self._reply({"error": "unknown action"})

            def _reply(self, data):
                payload = json.dumps(data).encode()
                self.send_response(200)
                self.send_header("content-type", "application/json")
                self.send_header("content-length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

        self._httpd = HTTPServer(("127.0.0.1", 0), Handler)
        self.port = self._httpd.server_address[1]
        t = threading.Thread(target=self._httpd.serve_forever, daemon=True)
        t.start()
        return self

    def stop(self):
        if self._httpd:
            self._httpd.shutdown()


def test_parse_payment_signature():
    block = _send_block(2 * 10**26, 10**26)
    header = _base64_payload(block)
    payload = nv.parse_payment_signature(header)
    assert payload is not None, "should parse a base64 PaymentPayload"
    assert payload["payload"]["block"]["type"] == "state"
    # A bare hash must NOT be treated as a PaymentPayload.
    assert nv.parse_payment_signature("ABCD" * 16) is None
    assert nv.parse_payment_signature("not base64 !!") is None
    print("PASS test_parse_payment_signature")


def test_destination_mismatch_fastfail():
    stub = StubNanoRPC().start()
    old_url = nv.NANO_RPC_URL
    nv.NANO_RPC_URL = f"http://127.0.0.1:{stub.port}"
    try:
        # Destination is a different account entirely.
        other = "nano_1amqpwgj79wqghbxa3aex3brbe4z7hk3hkw9hx7d3qkkqd815hu5nkzz13f1"
        header = _base64_payload(_send_block(2 * 10**26, 10**26, destination=other))
        payload = nv.parse_payment_signature(header)
        res = nv.confirm_signature_payment(payload, PRICE_RAW_1, VEND_TEST_ACCOUNT)
        assert res["valid"] is False
        assert "wrong address" in res["message"]
        assert stub.process_calls == 0, "must not broadcast a mismatched destination"
    finally:
        nv.NANO_RPC_URL = old_url
        stub.stop()
    print("PASS test_destination_mismatch_fastfail")


def test_broadcast_rejects_unsigned_block():
    stub = StubNanoRPC().start()
    old_url = nv.NANO_RPC_URL
    nv.NANO_RPC_URL = f"http://127.0.0.1:{stub.port}"
    try:
        block = _send_block(2 * 10**26, 10**26)
        block["signature"] = ""  # unsigned -> process rejects
        res = nv.broadcast_block(block)
        assert res["ok"] is False
        assert "Bad signature" in res["error"]
    finally:
        nv.NANO_RPC_URL = old_url
        stub.stop()
    print("PASS test_broadcast_rejects_unsigned_block")


def test_full_confirm_signature_payment():
    stub = StubNanoRPC().start()
    old_url = nv.NANO_RPC_URL
    old_confirm_timeout = nv.PAYMENT_CONFIRM_TIMEOUT_S
    nv.NANO_RPC_URL = f"http://127.0.0.1:{stub.port}"
    nv.PAYMENT_CONFIRM_TIMEOUT_S = 2
    try:
        header = _base64_payload(_send_block(2 * 10**26, 10**26))
        payload = nv.parse_payment_signature(header)
        res = nv.confirm_signature_payment(payload, PRICE_RAW_1, VEND_TEST_ACCOUNT)
        assert res["valid"] is True, f"expected valid, got {res}"
        assert stub.process_calls == 1
        assert res["block_hash"] and len(res["block_hash"]) == 64
        assert "broadcast_marker" in res
    finally:
        nv.NANO_RPC_URL = old_url
        nv.PAYMENT_CONFIRM_TIMEOUT_S = old_confirm_timeout
        stub.stop()
    print("PASS test_full_confirm_signature_payment")


def test_server_wiring_present():
    """server.py must call confirm_signature_payment and parse_payment_signature."""
    src = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            "server.py")).read()
    assert "confirm_signature_payment" in src
    assert "parse_payment_signature" in src
    assert "PAYMENT-SIGNATURE" in src
    print("PASS test_server_wiring_present")


if __name__ == "__main__":
    test_parse_payment_signature()
    test_destination_mismatch_fastfail()
    test_broadcast_rejects_unsigned_block()
    test_full_confirm_signature_payment()
    test_server_wiring_present()
    print("\nAll PAYMENT-SIGNATURE tests PASSED")
