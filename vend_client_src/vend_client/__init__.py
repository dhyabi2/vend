"""vend-client — Python client for Vend API Merchant.

Pay-per-call APIs settled in Nano (XNO) with no signup, no API key.
Each endpoint charges ~0.0001 XNO per call via x402 protocol.
"""

__version__ = "0.1.0"
__all__ = ["VendClient", "VendError"]

from vend_client.client import VendClient, VendError