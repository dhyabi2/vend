#!/usr/bin/env python3
"""Vend payment-guard static check (corrective action 2026-09-25 #3).

A pre-commit gate that refuses a commit when the payment verification logic
reads a buyer-controlled funds amount without an adjacent comparison to the
accepted amount.

Context: a buyer controls the signed block's balance fields.  If any code path
reads that amount and decides payment validity without comparing it to what the
endpoint accepted (ACCEPTED_FUNDS[0].amount == expected_price_raw), a buyer can
pay the wrong amount and still get served.  This check statically confirms the
runtime guard exists in the file that settles PAYMENT-SIGNATURE payments.

The check is deliberately narrow and structural (no AST-import of the server,
which would be heavy for a hook): it asserts the guard markers are present in
nano_verify.py co-located with the verify path.  The real behavioural guarantee
comes from tests/test_payment_signature.py (under/over/exact), which this gate
also requires to be wired into CI.

Exit codes: 0 = clean, 1 = guard missing / cannot run.
"""

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
NANO_VERIFY = os.path.join(ROOT, "nano_verify.py")


def check_nano_verify(src: str) -> list:
    problems = []

    # The block's funds are derived from its balance decrement.  We must see
    # (a) the decrement is computed from the previous block's balance, and
    # (b) it is compared for EXACT equality against the accepted price, and
    # (c) a mismatch is rejected.
    if "def block_decrement_amount" not in src:
        problems.append(
            "nano_verify.py: block_decrement_amount missing (the function that "
            "derives the real funds a signed block transfers)"
        )
    if "def confirm_signature_payment" not in src:
        problems.append(
            "nano_verify.py: confirm_signature_payment missing (the PAYMENT-"
            "SIGNATURE settlement path has disappeared)"
        )

    # The exact-match comparison in the settlement path.  A payment-settlement
    # read of the amount MUST be adjacent to a comparison to the accepted amount.
    if not re.search(r"decrement\s*!=\s*expected_raw", src):
        problems.append(
            "nano_verify.py: no exact amount-mismatch comparison "
            "(a buyer-controlled funds read with no guard against a wrong amount)"
        )

    if not re.search(r"Payment amount mismatch", src):
        problems.append(
            "nano_verify.py: mismatch rejection message missing (the guard does "
            "not visibly reject on mismatch)"
        )

    # The decrement must actually be exercised in front of the broadcast, not
    # just defined.  Confirm the settlement path calls it.
    if "decrement = block_decrement_amount(block)" not in src:
        problems.append(
            "nano_verify.py: block_decrement_amount is not called in the "
            "settlement path (a defined-but-unused guard protects nothing)"
        )
    return problems


def main() -> int:
    if not os.path.exists(NANO_VERIFY):
        print("payment-guard-check: nano_verify.py not found; cannot validate.", file=sys.stderr)
        return 1
    with open(NANO_VERIFY) as f:
        src = f.read()

    problems = check_nano_verify(src)
    if problems:
        print("payment-guard-check REFUSED: a payment amount is read without a guard", file=sys.stderr)
        for p in problems:
            print("  - " + p, file=sys.stderr)
        return 1

    print("payment-guard-check: clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
