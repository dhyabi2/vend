#!/usr/bin/env python3
"""x402dash utility with exponential backoff + jitter and local cache."""

import json, time, random, os, urllib.request, urllib.error

CACHE_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)) or ".", ".x402dash_cache.json")
BASE_URL = "https://api.x402dash.com/v1"

def x402dash_get(path, params=None, max_retries=3, use_cache=True):
    """GET from x402dash with exponential backoff + jitter. Falls back to cache on 429."""
    if params:
        import urllib.parse
        qs = urllib.parse.urlencode(params)
        url = f"{BASE_URL}/{path}?{qs}"
    else:
        url = f"{BASE_URL}/{path}"
    
    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "vend-probe/1.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < max_retries - 1:
                wait = (2 ** attempt) + random.random() * 2
                print(f"  Rate limited, retrying in {wait:.1f}s...", flush=True)
                time.sleep(wait)
                continue
            elif e.code == 429:
                print(f"  Rate limited (final), using cache", flush=True)
                return _load_cache()
            raise
    
    return _load_cache()

def _load_cache():
    """Load cached endpoints."""
    try:
        with open(CACHE_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"count": 0, "items": [], "error": "no cache"}

def refresh_cache():
    """Fetch ALL paypercall endpoints and cache them."""
    cache = x402dash_get("endpoints", {"q": "paypercall.dev"}, use_cache=False)
    cache["_cached_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f, indent=2)
    return cache

def find_endpoint(endpoint_id):
    """Find an endpoint in cache by ID substring."""
    cache = _load_cache()
    items = cache.get("items", [])
    for item in items:
        if endpoint_id in item.get("id", ""):
            return item
    return None

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "refresh":
        c = refresh_cache()
        print(f"Refreshed: {c.get('count', 0)} endpoints")
    else:
        c = _load_cache()
        print(f"Cache: {c.get('count', 0)} endpoints (from {c.get('_cached_at', 'unknown')})")
        for item in c.get("items", []):
            print(f"  {item.get('id','?'):50s} score={item.get('liveness_score','?')}")
