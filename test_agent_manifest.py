"""Laws for /.well-known/agent.json: the document the Open 402 validator accepts, built from server.py's rows."""
import agent_manifest as am

ROWS = [
    {"id": "extract-url", "name": "Extract URL Content", "description": "d1", "endpoint": "https://h/api/v1/extract",
     "method": "GET", "params": {"url": {"type": "string", "required": True}}, "price": 0.0001, "currency": "XNO"},
    {"id": "youtube-transcript", "name": "YouTube Transcript", "description": "first", "endpoint": "https://h/yt",
     "method": "GET", "params": {}, "price": 0.0005, "currency": "XNO"},
    {"id": "youtube-transcript", "name": "YouTube Transcript", "description": "second", "endpoint": "https://h/yt",
     "method": "GET", "params": {}, "price": 0.0005, "currency": "XNO"},
]


def build(rows=ROWS):
    return am.open402_manifest("h", "nano_1abc", "Vend", "desc", rows, "https://h", "c@h", "https://h", "2026-10-04T00:00:00Z")


def test_intent_names_are_snake_case_and_unique():
    names = [i["name"] for i in build()["intents"]]
    assert names == ["extract_url", "youtube_transcript"]
    assert all(am.NAME_RE.match(n) for n in names)


def test_a_duplicate_row_is_one_intent_and_the_first_wins():
    yt = [i for i in build()["intents"] if i["name"] == "youtube_transcript"]
    assert len(yt) == 1 and yt[0]["description"] == "first"


def test_an_xno_price_is_never_a_price_field():
    # the validator's price.currency is USD or USDC only; an XNO amount under `price` is a wrong claim
    for i in build()["intents"]:
        assert "price" not in i and "currency" not in i and "id" not in i and "params" not in i
        assert i["x-price"] == {"amount": i["x-price"]["amount"], "currency": "XNO", "network": "nano:mainnet"}
    assert build()["intents"][0]["x-price"]["amount"] == ROWS[0]["price"]


def test_network_and_asset_sit_where_the_claim_builder_reads_them():
    m = build()
    assert "x402" not in m, "the legacy top-level block is what failed validation"
    assert m["payments"]["x402"] == {"recipient": "nano_1abc", "networks": [{"network": "nano:mainnet", "asset": "XNO"}]}
    assert m["payout_address"] == "nano_1abc" and m["version"] == "1.3"


def test_unknown_top_level_fields_carry_the_extension_prefix():
    known = {"version", "origin", "payout_address", "display_name", "description", "intents", "payments"}
    assert all(k in known or k.startswith("x-") for k in build())


def test_a_row_id_that_cannot_be_a_name_is_refused_not_mangled():
    try:
        am.intent_name("---")
    except ValueError:
        return
    raise AssertionError("an unusable id must be refused")
