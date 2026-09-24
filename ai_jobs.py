"""
AI-jobs search for Vend.

Wraps the free, keyless artificialintelligencejobs.co feed API (19,800+ live
AI/AI-adjacent roles, updated daily) into a clean, bounded JSON endpoint for
agents doing labor-market research, lead-gen, competitor intelligence and
job-bot building. No signup, no key, no per-call cost upstream — the paywall
here is Vend's own.

Supported filters (all optional): q (full-text), company, category, region,
level, remote (1/true), plus limit (default 10, capped at 50) and offset for
pagination. Jobs are normalised to a clean union of fields so the caller gets
a stable shape regardless of which feed fields the upstream supplies.

Uses only the Python standard library (urllib + json). Priced at 0.0002 XNO
per call (a search over ~20k live postings, not a single URL).
"""

import json
import urllib.request
import urllib.parse

# The free keyless upstream feed. Returns JSON like
# {source, generated, total_live, matched, returned, offset, jobs:[...]}.
JOBS_API = "https://artificialintelligencejobs.co/api/jobs"
# Cap on how many jobs we return per call to keep responses bounded.
DEFAULT_LIMIT = 10
MAX_LIMIT = 50
# Guard against an absurdly large response from a hostile host.
MAX_BYTES = 2 * 1024 * 1024  # 2 MiB
_UA = "Vend/0.1 (Nano pay-per-call API; paypercall.dev)"

# Filters the upstream feed accepts. Anything else is ignored so we never
# forward a param the source does not understand (which silently no-ops).
SUPPORTED_FILTERS = ("q", "company", "category", "region", "level")

# Fields every job is normalised to; the source may provide a subset.
JOB_FIELDS = (
    "title", "company", "location", "category", "level", "region",
    "remote", "salary", "posted", "url", "apply_url", "company_url",
    "tags", "slug",
)


def _coerce_bool(value):
    """Normalise a user-supplied remote flag to True only for truthy inputs.

    Returns True for 1/true/yes/on, otherwise None (meaning 'no filter').
    """
    if value is None:
        return None
    v = str(value).strip().lower()
    return True if v in ("1", "true", "yes", "on") else None


def _normalise_job(job):
    """Return a clean dict with only JOB_FIELDS present (missing as None)."""
    out = {k: job.get(k) for k in JOB_FIELDS}
    return out


def ai_jobs(
    q=None,
    company=None,
    category=None,
    region=None,
    level=None,
    remote=None,
    limit=DEFAULT_LIMIT,
    offset=0,
    timeout: int = 15,
) -> dict:
    """Search the live AI-jobs feed with optional filters.

    Args:
        q, company, category, region, level: filter strings passed upstream.
        remote: truthy filter — include only remote roles when 1/true.
        limit: number of jobs to return (default 10, capped at 50).
        offset: pagination offset (default 0).
        timeout: HTTP timeout in seconds.

    Returns:
        dict with keys: source, generated, total_live, matched, returned,
        offset, filters, jobs (list of normalised job dicts), or error.
    """
    # Bound the user-controlled pagination to keep responses (and upstream
    # work) under control even if the caller asks for huge pages.
    try:
        limit = max(1, min(int(limit), MAX_LIMIT))
    except (TypeError, ValueError):
        limit = DEFAULT_LIMIT
    try:
        offset = max(0, int(offset))
    except (TypeError, ValueError):
        offset = 0

    params = {}
    filters = {}
    for name in SUPPORTED_FILTERS:
        value = locals().get(name)
        if value is not None and str(value).strip() != "":
            params[name] = str(value).strip()
            filters[name] = params[name]
    if _coerce_bool(remote):
        params["remote"] = "true"
        filters["remote"] = True
    params["limit"] = limit
    params["offset"] = offset

    url = JOBS_API + "?" + urllib.parse.urlencode(params)
    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": _UA,
                "Accept": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = resp.read(MAX_BYTES + 1)
            if len(data) > MAX_BYTES:
                return {"error": f"Upstream response exceeds {MAX_BYTES // (1024 * 1024)} MiB limit"}
            payload = json.loads(data.decode("utf-8", errors="replace"))
    except Exception as e:  # URLError, HTTPError, timeout, JSONDecodeError, etc.
        return {"error": f"Failed to fetch jobs feed: {str(e)[:200]}"}

    if not isinstance(payload, dict):
        return {"error": "Upstream returned an unexpected response shape"}

    jobs = payload.get("jobs") or []
    normalised = [_normalise_job(j) for j in jobs if isinstance(j, dict)]

    return {
        "source": payload.get("source", "artificialintelligencejobs.co"),
        "generated": payload.get("generated"),
        "total_live": payload.get("total_live"),
        "matched": payload.get("matched"),
        "returned": len(normalised),
        "offset": offset,
        "filters": filters,
        "jobs": normalised,
    }
