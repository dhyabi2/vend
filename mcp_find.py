"""
MCP/x402 service discovery — search public directories for paid agent services.

Searches agent-tools.cloud (primary, keyless) for MCP/x402 services matching
a query and returns structured results with settlement rails, prices and x402
health. A buyer uses this to answer "which paid service does this task for
a price I can pay in XNO?"

One verified source on launch: agent-tools.cloud (returns chains, prices,
x402_ok, payers_30d). Other keyless sources are added when the endpoint has
a paying caller who asks for them.

Synchronous by design so the module plugs into server.run_paid_work like the
other paid modules (extract, web_search, domain_info).

Priced at 0.0001 XNO per call (same as extract/web-search).
"""

import logging
from dataclasses import dataclass
from typing import Optional

import httpx

log = logging.getLogger("vend.mcp_find")

# ─── data types ────────────────────────────────────────────────────────

@dataclass
class ServiceResult:
    """Structured discovery result for one paid agent service."""
    name: str
    url: str
    description: str
    category: str
    chains: Optional[list]
    price_min: Optional[float]
    price_max: Optional[float]
    currency: Optional[str]
    x402_ok: Optional[bool]
    payers_30d: Optional[int]
    tx_30d: Optional[int]
    health: Optional[str]
    mcp_url: Optional[str]


# ─── sources ───────────────────────────────────────────────────────────

AGENT_TOOLS_API = "https://agent-tools.cloud/api/v1/search"


def _search_agent_tools(query: str, limit: int, client: httpx.Client) -> list[ServiceResult]:
    """Search agent-tools.cloud by query. Returns up to ``limit`` services."""
    try:
        resp = client.get(
            AGENT_TOOLS_API,
            params={"q": query, "limit": limit},
            headers={"Accept": "application/json"},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        log.warning("agent-tools.cloud search failed for %r: %s", query, e)
        return []

    services = data.get("services", []) if isinstance(data, dict) else []
    results = []
    for s in services[:limit]:
        if not isinstance(s, dict):
            continue
        results.append(ServiceResult(
            name=s.get("name", ""),
            url=s.get("url", ""),
            description=(s.get("description") or ""),
            category=s.get("category", ""),
            chains=s.get("chains", []),
            price_min=s.get("price_min"),
            price_max=s.get("price_max"),
            currency=s.get("currency"),
            x402_ok=bool(s.get("x402_ok")),
            payers_30d=s.get("payto_payers_30d"),
            tx_30d=s.get("tx_30d"),
            health=s.get("health"),
            mcp_url=s.get("mcp_url"),
        ))
    return results


# ─── top-level ─────────────────────────────────────────────────────────

_SOURCES = [
    ("agent-tools.cloud", _search_agent_tools),
]


def _matches_rail(chains: list, filter_rail: str) -> bool:
    """True if any chain's scheme matches the requested rail (case-insensitive).

    A chain entry may be bare ("base") or scoped ("nano:mainnet",
    "eip155:8453"). The rail is compared against the scheme before the colon,
    so "nano" matches "nano:mainnet" and "base" matches "base".
    """
    rl = filter_rail.lower()
    for c in chains or []:
        scheme = (c or "").lower().split(":")[0]
        if scheme == rl or rl == scheme:
            return True
    return False


def mcp_find(
    query: str,
    limit: int = 10,
    filter_rail: Optional[str] = None,
) -> dict:
    """Search MCP/x402 service directories for paid services matching *query*.

    Args:
        query: Natural-language search — what the service does.
        limit: Max results to return (default 10, max 50).
        filter_rail: Optional rail filter — pass ``"nano"`` to show only
            services that accept Nano (XNO) settlement; ``"base"`` for USDC
            on Base, etc.

    Returns:
        dict with keys:
            query: the search query used.
            filter_rail: the rail filter (or None).
            source: which directory answered.
            results: list of matched service dicts.
            result_count: number of results.
            error: on catastrophic failure.
    """
    query = (query or "").strip()
    if not query:
        return {"error": "query parameter is required"}

    limit = min(max(limit, 1), 50)

    with httpx.Client() as client:
        for source_name, source_fn in _SOURCES:
            results = source_fn(query, limit, client)
            if not results:
                continue
            dicts = []
            for r in results:
                item = {
                    "name": r.name,
                    "url": r.url,
                    "description": r.description,
                    "category": r.category,
                    "chains": r.chains or [],
                    "price_min": r.price_min,
                    "price_max": r.price_max,
                    "currency": r.currency,
                    "x402_ok": r.x402_ok,
                    "payers_30d": r.payers_30d,
                    "health": r.health,
                    "mcp_url": r.mcp_url,
                }
                if filter_rail and not _matches_rail(r.chains, filter_rail):
                    continue
                dicts.append(item)
            return {
                "query": query,
                "filter_rail": filter_rail,
                "source": source_name,
                "results": dicts,
                "result_count": len(dicts),
            }

    return {
        "query": query,
        "filter_rail": filter_rail,
        "source": None,
        "results": [],
        "result_count": 0,
        "error": "all discovery sources failed",
    }
