"""The shape of /.well-known/agent.json that the published validator accepts.

server.py describes each paid endpoint once, in the rows it has always written (id, title, params, a price in
XNO). `agent-json-validate@1.4.0` - the validator the Open 402 directory crawls with - refused that document
with 32 errors on 2026-10-04: a legacy `x402` block with no `supported`, intent names that were titles, a bare
number where `price` must be an object, and one intent listed twice. Its `price.currency` accepts only USD or
USDC, so an XNO price cannot be a `price` at all: it travels as `x-price`, and the settlement network and asset
are declared where the directory's claim builder reads them, `payments.x402.networks`.

Pure, no imports from server.py, so the laws can run without starting the app.
"""
import re

NAME_RE = re.compile(r"^[a-z][a-z0-9_]*$")
NETWORK = "nano:mainnet"
ASSET = "XNO"


def intent_name(row_id):
    name = re.sub(r"[^a-z0-9]+", "_", str(row_id).lower()).strip("_")
    if not NAME_RE.match(name):
        raise ValueError(f"cannot make an intent name from {row_id!r}")
    return name


def open402_manifest(origin, account, display_name, description, rows, api_base, contact, docs_url, updated):
    intents, seen = [], set()
    for row in rows:
        name = intent_name(row["id"])
        if name in seen:  # the same endpoint described twice is one intent, the first description wins
            continue
        seen.add(name)
        intents.append({
            "name": name,
            "description": row["description"],
            "endpoint": row["endpoint"],
            "method": row["method"],
            "parameters": row.get("params", {}),
            "x-title": row["name"],
            "x-price": {"amount": row["price"], "currency": ASSET, "network": NETWORK},
        })
    return {
        "version": "1.3",
        "origin": origin,
        "payout_address": account,
        "display_name": display_name,
        "description": description,
        "intents": intents,
        "payments": {"x402": {"recipient": account, "networks": [{"network": NETWORK, "asset": ASSET}]}},
        "x-api-base": api_base,
        "x-contact": contact,
        "x-docs-url": docs_url,
        "x-updated": updated,
    }
