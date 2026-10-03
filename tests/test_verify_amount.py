"""The amount check in verify_payment must fail closed.

A ledger response that carries no usable ``amount`` (an empty string, a null,
an RPC proxy that drops the field) used to skip the price comparison and come
back ``valid: True``, which served paid endpoints for free.
"""

import nano_verify


PAYER = "nano_1payer3zf1p4ym5rkw9s9bnfkqfhzjrz9ygz8oi6mqzzqzzqzzqzzqzzqzz"


def _block(amount):
    return {
        "amount": amount,
        "contents": {
            "account": PAYER,
            "link_as_account": nano_verify.VEND_ACCOUNT,
        },
    }


def _verify_with(monkeypatch, amount):
    monkeypatch.setattr(nano_verify, "check_block_exists", lambda h: _block(amount))
    return nano_verify.verify_payment(
        "A" * 64, nano_verify.PRICE_RAW, nano_verify.VEND_ACCOUNT
    )


def test_empty_amount_is_refused(monkeypatch):
    result = _verify_with(monkeypatch, "")
    assert result["valid"] is False
    assert "amount" in result["message"].lower()


def test_null_amount_is_refused(monkeypatch):
    result = _verify_with(monkeypatch, None)
    assert result["valid"] is False


def test_non_numeric_amount_is_refused(monkeypatch):
    result = _verify_with(monkeypatch, "not-a-number")
    assert result["valid"] is False


def test_unparseable_price_is_refused(monkeypatch):
    """A misconfigured price must not wave payments through either."""
    monkeypatch.setattr(nano_verify, "check_block_exists", lambda h: _block("10" + "0" * 26))
    result = nano_verify.verify_payment("A" * 64, "", nano_verify.VEND_ACCOUNT)
    assert result["valid"] is False


def test_short_payment_still_refused(monkeypatch):
    result = _verify_with(monkeypatch, "1")
    assert result["valid"] is False
    assert "too small" in result["message"]


def test_sufficient_payment_still_accepted(monkeypatch):
    result = _verify_with(monkeypatch, nano_verify.PRICE_RAW)
    assert result["valid"] is True
    assert result["source"] == PAYER
