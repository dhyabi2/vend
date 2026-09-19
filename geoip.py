"""
IP Geolocation using ip-api.com — free, no API key needed.

Returns structured location data (country, city, coordinates, ISP, ASN)
for any IPv4/IPv6 address. No upstream API costs — the free tier
handles 45 requests/minute without a key.

Priced at 0.0001 XNO per call.
"""

import logging
import urllib.request
import json

log = logging.getLogger("vend.geoip")

FIELDS = (
    "status,message,continent,continentCode,country,countryCode,"
    "region,regionName,city,zip,lat,lon,timezone,isp,org,as,asname,query"
)

# ─── main entry ────────────────────────────────────────────────────────────


def geoip_lookup(ip: str) -> dict:
    """Look up geolocation data for an IP address.

    Args:
        ip: IPv4 or IPv6 address (e.g. "8.8.8.8"). Also accepts "myip"
            as a special value to look up the caller's own IP.

    Returns:
        dict with keys: query (the IP), status, country, city, lat, lon,
        isp, org, asn, timezone, region, etc., or error on failure.
    """
    if not ip or not ip.strip():
        return {"error": "ip parameter is required"}

    ip = ip.strip()

    # No cost to normalise; and ip-api.com doesn't support "myip" so we
    # resolve it client-side through a free third-party service.
    if ip.lower() in ("myip", "my", "me", ""):
        try:
            resp = urllib.request.urlopen(
                "https://api.ipify.org?format=json", timeout=10
            )
            data = json.loads(resp.read().decode())
            ip = data.get("ip", "")
        except Exception as e:
            return {"error": f"could not determine your IP: {e}"}

    try:
        url = f"http://ip-api.com/json/{ip}?fields={FIELDS}"
        resp = urllib.request.urlopen(url, timeout=15)
        result = json.loads(resp.read().decode())
    except Exception as e:
        log.warning("IP geolocation lookup for %r failed: %s", ip, e)
        return {"error": f"lookup backend error: {e}"}

    if result.get("status") == "fail":
        msg = result.get("message", "invalid IP address")
        return {"query": ip, "error": msg}

    return {
        "query": result.get("query", ip),
        "status": result.get("status"),
        "continent": result.get("continent"),
        "continent_code": result.get("continentCode"),
        "country": result.get("country"),
        "country_code": result.get("countryCode"),
        "region": result.get("region"),
        "region_name": result.get("regionName"),
        "city": result.get("city"),
        "zip": result.get("zip"),
        "latitude": result.get("lat"),
        "longitude": result.get("lon"),
        "timezone": result.get("timezone"),
        "isp": result.get("isp"),
        "org": result.get("org"),
        "asn": result.get("as"),
        "asn_name": result.get("asname"),
    }