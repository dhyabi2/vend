"""Tests for CDP verify module — no server, no CDP credentials needed."""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))


def test_bazaar_extension_structure():
    """Bazaar extension has required info.input block."""
    from cdp_verify import build_bazaar_extension

    ext = build_bazaar_extension("/api/v1/extract", "GET")
    assert "info" in ext
    assert ext["info"]["input"]["type"] == "http"
    assert ext["info"]["input"]["method"] == "GET"
    assert "schema" in ext["info"]["input"]


def test_bazaar_extension_with_input_schema():
    """Bazaar extension accepts a custom input schema."""
    from cdp_verify import build_bazaar_extension

    schema = {
        "type": "object",
        "properties": {"url": {"type": "string"}},
        "required": ["url"],
    }
    ext = build_bazaar_extension("/api/v1/extract", "GET", input_schema=schema)
    assert ext["info"]["input"]["schema"] == schema


def test_usdc_accept_no_address():
    """build_usdc_accept returns None without an EVM address."""
    from cdp_verify import build_usdc_accept

    result = build_usdc_accept(0.0001, pay_to_address=None)
    assert result is None


def test_usdc_accept_with_address():
    """A valid USDC accept entry is returned with proper fields."""
    from cdp_verify import build_usdc_accept

    addr = "0x1234567890abcdef1234567890abcdef12345678"
    result = build_usdc_accept(0.0001, pay_to_address=addr)
    assert result is not None
    assert result["scheme"] == "exact"
    assert result["network"] == "eip155:8453"
    assert result["asset"] == "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
    assert result["payTo"] == addr
    assert result["amount"] == "100"  # 0.0001 USDC = 100 base units
    assert result["maxTimeoutSeconds"] == 60


def test_usdc_accept_custom_amount():
    """Custom USDC price overrides the default."""
    from cdp_verify import build_usdc_accept

    addr = "0x1234567890abcdef1234567890abcdef12345678"
    result = build_usdc_accept(0.0005, pay_to_address=addr, usdc_price_raw="500")
    assert result["amount"] == "500"


def test_price_conversion():
    """price_usdc_to_amount converts USD prices to raw USDC amounts (6 decimals)."""
    from cdp_verify import price_usdc_to_amount

    assert price_usdc_to_amount(0.0001) == "100"
    assert price_usdc_to_amount(0.001) == "1000"
    assert price_usdc_to_amount(0.01) == "10000"
    assert price_usdc_to_amount(0.10) == "100000"
    assert price_usdc_to_amount(1.0) == "1000000"


def test_usdc_accept_rounds_safely():
    """USDC amount is rounded, not truncated."""
    from cdp_verify import price_usdc_to_amount

    # 0.0000001 should round to 0
    assert price_usdc_to_amount(0.0000001) == "0"


def test_cdp_credentials_no_env():
    """Without env variables, credentials check returns False."""
    from cdp_verify import check_cdp_credentials, usdc_pay_to_address

    # Ensure env is clean
    for k in ("CDP_API_KEY_ID", "CDP_API_KEY_SECRET", "VEND_USDC_ADDRESS"):
        if k in os.environ:
            del os.environ[k]

    assert check_cdp_credentials() is False
    assert usdc_pay_to_address() is None


def test_bazaar_in_challenge():
    """build_402_challenge now always includes the bazaar extension."""
    from nano_verify import build_402_challenge

    chal = build_402_challenge("/api/v1/extract")
    ext = chal.get("extensions", {})
    assert "bazaar" in ext, "Bazaar extension should always be present"
    assert "info" in ext["bazaar"], "Bazaar should have info block"


def test_challenge_accepts_nano():
    """Nano accept is always present in the challenge."""
    from nano_verify import build_402_challenge

    chal = build_402_challenge("/api/v1/extract")
    accepts = chal.get("accepts", [])
    nano_accepts = [a for a in accepts if a.get("network") == "nano:mainnet"]
    assert len(nano_accepts) == 1
    assert nano_accepts[0]["asset"] == "XNO"


def test_challenge_no_usdc_without_env():
    """Without VEND_USDC_ADDRESS, only 1 accept (Nano)."""
    from nano_verify import build_402_challenge

    # Ensure env is clean
    for k in ("VEND_USDC_ADDRESS",):
        if k in os.environ:
            del os.environ[k]

    chal = build_402_challenge("/api/v1/extract")
    assert len(chal["accepts"]) == 1


def test_validate_endpoint_keyless():
    """CDP validate endpoint is callable without credentials."""
    from cdp_verify import validate_endpoint

    # This is a keyless endpoint that should always return a result
    # shape, even if validation fails
    result = validate_endpoint("https://extract.paypercall.dev/api/v1/extract?url=https://example.com")
    assert "valid" in result
    assert "preflight" in result
    assert isinstance(result["preflight"], list)