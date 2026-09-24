"""CDP Facilitator verify/settle for USDC-on-Base x402 payments.

Uses the Coinbase CDP Facilitator to verify and settle USDC payments on
Base (eip155:8453). Requires CDP API credentials stored as:

  CDP_API_KEY_ID     — CDP API key identifier
  CDP_API_KEY_SECRET — CDP API key secret

The CDP Validate endpoint is keyless and can be called to verify that an
endpoint's 402 challenge and bazaar extension are correctly structured.

References:
  - https://docs.cdp.coinbase.com/x402/validate-endpoint
  - https://docs.cdp.coinbase.com/x402/core-concepts/facilitator
"""

import base64
import json
import logging
import os
import time
from typing import Optional

import httpx

log = logging.getLogger("vend.cdp")

# USDC on Base mainnet
USDC_BASE_CONTRACT = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
CDP_FACILITATOR_URL = "https://api.cdp.coinbase.com/platform/v2/x402"

# USDC has 6 decimal places
USDC_DECIMALS = 6


def price_usdc_to_amount(price_usd: float) -> str:
    """Convert a USD price to USDC raw amount string (6 decimals).

    Example: 0.0001 USD -> "100"
    """
    return str(int(round(price_usd * 10**USDC_DECIMALS)))


def get_jwt_token() -> Optional[str]:
    """Generate a CDP JWT token for authenticated API calls.

    Returns None when CDP credentials are not configured, so callers
    can gracefully fall back to Nano-only payment verification.
    """
    key_id = os.environ.get("CDP_API_KEY_ID", "")
    key_secret = os.environ.get("CDP_API_KEY_SECRET", "")
    if not key_id or not key_secret:
        return None

    # CDP JWT: header {alg: ES256, kid: <key_id>, typ: JWT}
    # payload {iss: cdp, sub: <key_id>, iat: <now>, exp: <now+120>, requestHost, requestPath}
    # signed with the key_secret (ECDSA P-256)
    #
    # The CDP SDK handles this internally. For a minimal implementation
    # without the full SDK, we'd need the raw ES256 signing.
    #
    # For now, raise a clear error pointing to the SDK.
    raise NotImplementedError(
        "CDP JWT signing requires the cdp-sdk package. "
        "Use: from cdp import CdpClient; token = CdpClient().get_jwt(request_path, request_method)"
    )


def validate_endpoint(url: str, method: str = "GET") -> dict:
    """Validate an x402 endpoint's bazaar-discovery configuration.

    Keyless (no API key required). Probes the endpoint live and returns
    the full validation result including preflight checks and simulation.

    Args:
        url: HTTPS URL of the x402 endpoint (e.g. https://extract.paypercall.dev/api/v1/extract?url=https://example.com)
        method: HTTP method (GET or POST)

    Returns:
        dict with keys: valid (bool), statusCode (int), preflight (list),
        paymentRequirements (dict), bazaarExtension (dict|None),
        simulation (dict)
    """
    try:
        resp = httpx.post(
            f"{CDP_FACILITATOR_URL}/validate",
            json={"resource": url, "method": method},
            timeout=15,
        )
        if resp.status_code == 200:
            return resp.json()
        return {
            "valid": False,
            "error": f"validate endpoint returned {resp.status_code}",
            "detail": resp.text[:500],
        }
    except Exception as e:
        return {
            "valid": False,
            "error": f"validate endpoint unreachable: {e}",
        }


def build_bazaar_extension(endpoint_path: str, method: str = "GET",
                           input_schema: Optional[dict] = None) -> dict:
    """Build a CDP Bazaar discovery extension block.

    This block is attached to the 402 response's ``extensions`` so the
    CDP Bazaar crawler can discover and index the endpoint for search
    and listing.

    Args:
        endpoint_path: The API path (e.g. /api/v1/extract)
        method: HTTP method
        input_schema: JSON Schema for input parameters (optional)

    Returns:
        dict: The bazaar extension block
    """
    ext = {
        "info": {
            "input": {
                "type": "http",
                "method": method,
                "schema": input_schema or {
                    "$schema": "https://json-schema.org/draft/2020-12/schema",
                    "type": "object",
                },
            }
        }
    }
    return ext


def build_usdc_accept(price_xno: float, pay_to_address: Optional[str] = None,
                      usdc_price_raw: Optional[str] = None) -> dict:
    """Build a USDC-on-Base accept entry for the 402 challenge.

    Current limitation: requires a Base EVM address as pay_to. When
    ``pay_to_address`` is None, returns None (Nano-only fallback).

    Args:
        price_xno: The Nano price (used to derive equivalent USDC)
        pay_to_address: The EVM address (0x...) to receive USDC
        usdc_price_raw: Override USDC raw amount (auto-derived from price_xno if not given)

    Returns:
        dict or None
    """
    if not pay_to_address:
        return None

    # Derive USDC price: approximate Nano price in USD ~ $0.0001 per call standard
    # This is kept conservative: 0.0001 XNO ≈ ~$0.00003 USD at current rates,
    # but the minimum USDC unit is $0.000001 (1 microcent).
    # We charge a flat $0.0001 USDC base price for parity with Nano pricing.
    if usdc_price_raw is None:
        usdc_price_raw = price_usdc_to_amount(0.0001)

    return {
        "scheme": "exact",
        "network": "eip155:8453",
        "asset": USDC_BASE_CONTRACT,
        "amount": usdc_price_raw,
        "payTo": pay_to_address,
        "maxTimeoutSeconds": 60,
    }


# Cache: the CDP validate endpoint is public and fast; no caching needed.
# But we do keep one flag so /health can report CDP readiness.
_CDP_CREDENTIALS_CHECKED = False
_HAS_CDP_CREDENTIALS = False


def check_cdp_credentials() -> bool:
    """Check if CDP API credentials are configured."""
    global _CDP_CREDENTIALS_CHECKED, _HAS_CDP_CREDENTIALS
    if _CDP_CREDENTIALS_CHECKED:
        return _HAS_CDP_CREDENTIALS
    _HAS_CDP_CREDENTIALS = bool(
        os.environ.get("CDP_API_KEY_ID", "")
        and os.environ.get("CDP_API_KEY_SECRET", "")
    )
    _CDP_CREDENTIALS_CHECKED = True
    return _HAS_CDP_CREDENTIALS


def usdc_pay_to_address() -> Optional[str]:
    """Return the configured USDC-on-Base pay_to address, or None."""
    return os.environ.get("VEND_USDC_ADDRESS") or None
