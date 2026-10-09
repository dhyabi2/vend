"""An on-ledger send that the node has not confirmed is not a payment yet.

While a send is unconfirmed the account that signed it can publish a second
block off the same ``previous`` -- a fork -- and only one of the two survives
the representatives' vote.  ``block_info`` reports ``confirmed`` in the same
response the verifier already reads, so a payer could hand Vend the hash of the
fork that pays Vend, be served, and keep the money.

Both settlement dialects are covered:

* ``X-PAYMENT`` (the buyer broadcast it themselves) -- ``verify_payment``
  refuses. It is called before ``store.redeem``, so the block is not marked
  spent and the same hash is served on a retry once it confirms.
* ``PAYMENT-SIGNATURE`` (Vend broadcast it) -- ``wait_for_confirmation`` keeps
  polling inside its existing timeout budget instead of returning on the first
  on-ledger sighting.

An absent ``confirmed`` field is "we do not know" and keeps the old behaviour,
so an RPC proxy that drops the field can never take the paywall down.
"""

import nano_verify


PAYER = "nano_1payer3zf1p4ym5rkw9s9bnfkqfhzjrz9ygz8oi6mqzzqzzqzzqzzqzzqzz"
ENOUGH = nano_verify.PRICE_RAW


def _block(confirmed=..., amount=ENOUGH):
    info = {
        "amount": amount,
        "contents": {
            "account": PAYER,
            "link_as_account": nano_verify.VEND_ACCOUNT,
        },
    }
    if confirmed is not ...:
        info["confirmed"] = confirmed
    return info


def _verify(monkeypatch, info):
    monkeypatch.setattr(nano_verify, "check_block_exists", lambda h: info)
    return nano_verify.verify_payment(
        "A" * 64, nano_verify.PRICE_RAW, nano_verify.VEND_ACCOUNT
    )


# ── X-PAYMENT: the refusal ───────────────────────────────────────────

def test_an_unconfirmed_block_is_refused(monkeypatch):
    """The node's own string form, which is what Nano's RPC sends."""
    result = _verify(monkeypatch, _block(confirmed="false"))
    assert result["valid"] is False
    assert "confirm" in result["message"].lower()


def test_an_unconfirmed_block_is_refused_as_a_json_boolean(monkeypatch):
    """A JSON-typed proxy may send the boolean rather than the string."""
    result = _verify(monkeypatch, _block(confirmed=False))
    assert result["valid"] is False


def test_the_refusal_says_no_payment_was_taken(monkeypatch):
    """The buyer must know to retry with the same hash, not to pay again."""
    result = _verify(monkeypatch, _block(confirmed="false"))
    assert "again" in result["message"].lower()


def test_a_short_unconfirmed_payment_is_still_refused_for_being_short(monkeypatch):
    """The amount check runs first; the confirmation check does not mask it."""
    result = _verify(monkeypatch, _block(confirmed="false", amount="1"))
    assert result["valid"] is False
    assert "too small" in result["message"]


# ── X-PAYMENT: the controls, which must hold either way ──────────────

def test_a_confirmed_block_is_accepted(monkeypatch):
    result = _verify(monkeypatch, _block(confirmed="true"))
    assert result["valid"] is True, result["message"]


def test_a_response_with_no_confirmed_field_is_accepted(monkeypatch):
    """Fail open: an RPC proxy that drops the field cannot stop a sale."""
    result = _verify(monkeypatch, _block())
    assert result["valid"] is True, result["message"]


def test_an_unreadable_confirmed_field_is_accepted(monkeypatch):
    """Only an explicit negative refuses; anything else is 'we do not know'."""
    for value in ("", "   ", "unknown", None, 0, [], {}):
        result = _verify(monkeypatch, _block(confirmed=value))
        assert result["valid"] is True, f"{value!r}: {result['message']}"


def test_the_amount_and_payer_are_still_reported_on_the_refusal(monkeypatch):
    result = _verify(monkeypatch, _block(confirmed="false"))
    assert result["amount_raw"] == ENOUGH
    assert result["source"] == PAYER


def test_a_wrong_destination_is_still_refused_when_confirmed(monkeypatch):
    info = _block(confirmed="true")
    info["contents"]["link_as_account"] = PAYER
    result = _verify(monkeypatch, info)
    assert result["valid"] is False
    assert "wrong address" in result["message"]


# ── PAYMENT-SIGNATURE: the wait ──────────────────────────────────────

def test_wait_for_confirmation_does_not_return_on_an_unconfirmed_sighting(monkeypatch):
    """It must not call an unconfirmed block confirmed. Its budget is for this."""
    monkeypatch.setattr(nano_verify, "check_block_exists",
                        lambda h: _block(confirmed="false"))
    monkeypatch.setattr(nano_verify.time, "sleep", lambda s: None)
    res = nano_verify.wait_for_confirmation("A" * 64, timeout_s=0.05, poll_s=0.01)
    assert res["confirmed"] is False
    assert "unconfirmed" in res["error"]


def test_wait_for_confirmation_returns_once_the_vote_lands(monkeypatch):
    """The ordinary case: unconfirmed on the first poll, confirmed on the next."""
    answers = [_block(confirmed="false"), _block(confirmed="true")]
    monkeypatch.setattr(nano_verify, "check_block_exists",
                        lambda h: answers.pop(0) if answers else _block(confirmed="true"))
    monkeypatch.setattr(nano_verify.time, "sleep", lambda s: None)
    res = nano_verify.wait_for_confirmation("A" * 64, timeout_s=5, poll_s=0.01)
    assert res["confirmed"] is True
    assert answers == []


def test_wait_for_confirmation_still_returns_with_no_confirmed_field(monkeypatch):
    """Fail open here too, or the signature dialect would stall for its budget."""
    monkeypatch.setattr(nano_verify, "check_block_exists", lambda h: _block())
    res = nano_verify.wait_for_confirmation("A" * 64, timeout_s=5, poll_s=0.01)
    assert res["confirmed"] is True


def test_wait_for_confirmation_still_fails_fast_on_a_rejected_block(monkeypatch):
    monkeypatch.setattr(nano_verify, "check_block_exists",
                        lambda h: {"error": "Block not found"})
    res = nano_verify.wait_for_confirmation("A" * 64, timeout_s=5, poll_s=0.01)
    assert res["confirmed"] is False
    assert "Block not found" in res["error"]


# ── the predicate itself ─────────────────────────────────────────────

def test_the_predicate_reads_only_an_explicit_negative():
    f = nano_verify._is_explicitly_unconfirmed
    assert f({"confirmed": "false"}) is True
    assert f({"confirmed": "FALSE"}) is True
    assert f({"confirmed": " false "}) is True
    assert f({"confirmed": False}) is True
    assert f({"confirmed": "true"}) is False
    assert f({"confirmed": True}) is False
    assert f({}) is False
    assert f(None) is False
