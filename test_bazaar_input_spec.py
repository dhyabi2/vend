"""Test that every paid endpoint registered in endpoint_meta has a usable bazaar input schema.

Guards join:#345 (2026-09-24): a discovering x402 agent builds its first (paid)
request from extensions.bazaar.info.input.schema in the 402 challenge. When that
schema was empty (type:object with no properties) for select/links/meta/table/
wiki-summary/arxiv-paper, an agent could not know what parameter to send and so
failed closed instead of paying.

The bazaar input spec comes from endpoint_meta.INPUT_SPECS, which require_payment
reads so a 402 challenge carries it. Verifying the registry directly is the
durable guard: a paid endpoint registered without an input spec re-introduces the
empty-schema bug.

The contract is honest when:
  - every endpoint in INPUT_SPECS declares its query properties;
  - the endpoints that were empty live (select, links, meta, table, wiki-summary,
    arxiv-paper) are registered with properties and their required params;
  - required parameters are declared as required.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# The endpoints that shipped with an EMPTY bazaar input schema live (join:#345),
# now registered. This anchors the regression without depending on which other
# endpoints a given base registers.
EMPTY_SCHEMA_ENDPOINTS = [
    "/api/v1/select",
    "/api/v1/links",
    "/api/v1/meta",
    "/api/v1/table",
    "/api/v1/wiki-summary",
    "/api/v1/arxiv-paper",
]


def test_no_registered_endpoint_has_an_empty_input_schema():
    """Every endpoint in INPUT_SPECS must declare properties in its input.schema
    -- an empty schema (join:#345) means a discovering agent cannot know what to
    send, so it fails closed instead of paying."""
    from endpoint_meta import INPUT_SPECS
    assert INPUT_SPECS, "INPUT_SPECS must not be empty"
    for ep, spec in INPUT_SPECS.items():
        props = (spec.get("input", {}).get("schema", {}) or {}).get("properties")
        assert props, (
            f"{ep} INPUT_SPECS input.schema has no properties (join:#345)")


def test_previously_empty_endpoints_are_registered():
    """The endpoints that advertised an empty bazaar schema live must now be in
    INPUT_SPECS with their query parameters declared (join:#345)."""
    from endpoint_meta import INPUT_SPECS
    for ep in EMPTY_SCHEMA_ENDPOINTS:
        spec = INPUT_SPECS.get(ep, {})
        props = (spec.get("input", {}).get("schema", {}) or {}).get("properties")
        assert props, (
            f"{ep} still missing a bazaar input spec (join:#345)")


def test_required_params_are_declared():
    """Endpoints whose handlers require a param must declare it as required in the
    bazaar input schema (extract url, select url+selector, links url, etc.)."""
    from endpoint_meta import INPUT_SPECS
    required_check = {
        "/api/v1/extract": "url",
        "/api/v1/select": "selector",
        "/api/v1/links": "url",
        "/api/v1/wiki-summary": "q",
        "/api/v1/geoip": "ip",
    }
    for path, req_param in required_check.items():
        spec = INPUT_SPECS.get(path, {})
        req = spec.get("input", {}).get("schema", {}).get("required") or []
        assert req_param in req, (
            f"{path} must declare {req_param} as required in its bazaar input schema")


def test_every_advertised_endpoint_has_a_bazaar_input_spec():
    """The empty-schema guard must not only iterate what INPUT_SPECS happens to
    contain: an endpoint the product advertises but forgot to register would
    then pass (review-block on #354). Every path the server advertises as a paid
    endpoint (ARD_RESOURCES) must be registered here with non-empty properties,
    so a new endpoint cannot silently ship without a schema a discovering agent
    can copy."""
    import server as _server
    advertised = {entry[1] for entry in _server.ARD_RESOURCES
                  if entry[1].startswith("/api/v1/")}
    assert advertised, "ARD_RESOURCES must advertise at least one paid endpoint"
    from endpoint_meta import INPUT_SPECS
    registered = set(INPUT_SPECS)
    # every advertised endpoint must be registered
    missing = advertised - registered
    assert not missing, (
        f"endpoint(s) advertised but missing a bazaar input spec (join:#345): "
        f"{sorted(missing)}")
    # and each registered one must carry usable properties
    for ep in advertised:
        props = (INPUT_SPECS.get(ep, {}).get("input", {}).get("schema", {}) or {}).get("properties")
        assert props, f"{ep} INPUT_SPECS input.schema has no properties (join:#345)"
    # a schema example an agent copies must not contradict its declared type
    for ep in advertised:
        spec = INPUT_SPECS.get(ep, {})
        schema = (spec.get("input", {}).get("schema", {}) or {})
        for name, prop in (schema.get("properties") or {}).items():
            declared = prop.get("type")
            ex = (spec.get("input", {}).get("example") or {}).get(name)
            if ex is None or declared not in ("integer", "boolean"):
                continue
            if declared == "integer":
                assert isinstance(ex, int) and not isinstance(ex, bool), (
                    f"{ep} example[{name}]={ex!r} must be an integer, not a string (review #354)")
            if declared == "boolean":
                assert isinstance(ex, bool), (
                    f"{ep} example[{name}]={ex!r} must be a boolean, not a string (review #354)")
