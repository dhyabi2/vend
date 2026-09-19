"""Domain information lookup — DNS, WHOIS, SSL/TLS certificate data.

Runs system tools (dig, openssl, whois) to gather intelligence about a domain.
Returns structured JSON suitable for agent decision-making.

Costs nothing per call at scale — zero upstream API dependencies.
"""

import json
import logging
import re
import subprocess
import socket
import ssl
import time
from typing import Optional
from urllib.parse import urlparse

log = logging.getLogger("vend.domain_info")

# ─── helpers ──────────────────────────────────────────────────────────────


def _run(cmd: list[str], timeout: int = 10) -> str:
    """Run a command and return its stdout, or '' on failure."""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip() if r.returncode == 0 else ""
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as e:
        log.warning("cmd failed: %s — %s", " ".join(cmd), e)
        return ""


def _clean_domain(raw: str) -> Optional[str]:
    """Normalise a domain input — strip protocol, path, trailing dots."""
    if not raw or not raw.strip():
        return None
    raw = raw.strip().lower()
    # Remove protocol prefix if present
    if "://" in raw:
        raw = urlparse(raw).hostname or raw
    # Remove trailing dot and path
    raw = raw.split("/")[0].rstrip(".")
    # Basic domain validation (at least one dot, no spaces)
    if "." not in raw or not re.match(r"^[a-z0-9]([a-z0-9\-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9\-]*[a-z0-9])?)+$", raw):
        return None
    return raw


# ─── DNS lookups ─────────────────────────────────────────────────────────


def _dns_lookup(domain: str) -> dict:
    """Perform DNS lookups for common record types using `dig`."""
    result = {}
    for rtype in ("A", "AAAA", "MX", "NS", "TXT", "CNAME", "SOA"):
        try:
            out = _run(["dig", "+short", "+time=5", "+tries=2", rtype, domain])
            if out:
                if rtype == "MX":
                    lines = [l.split() for l in out.split("\n") if l.strip()]
                    result[rtype] = [{"priority": int(p), "target": t} for p, t in lines if len(lines) > 0]
                elif rtype == "SOA" and out:
                    parts = out.split()
                    if len(parts) >= 7:
                        result[rtype] = {
                            "mname": parts[0], "rname": parts[1],
                            "serial": parts[2], "refresh": parts[3],
                            "retry": parts[4], "expire": parts[5],
                            "minimum": parts[6],
                        }
                else:
                    result[rtype] = [l.strip() for l in out.split("\n") if l.strip()]
        except Exception as e:
            log.warning("dig %s %s failed: %s", rtype, domain, e)
    return result


# ─── WHOIS / RDAP lookup ────────────────────────────────────────────────


def _whois_lookup(domain: str) -> dict:
    """Look up domain registration data via whois/RDAP."""
    try:
        import whois as whois_lib
        w = whois_lib.whois(domain)
        return {
            "registrar": w.registrar or "",
            "registrant": w.name or "",
            "creation_date": str(w.creation_date[0]) if isinstance(w.creation_date, list) and w.creation_date else (
                str(w.creation_date) if w.creation_date else ""),
            "expiration_date": str(w.expiration_date[0]) if isinstance(w.expiration_date, list) and w.expiration_date else (
                str(w.expiration_date) if w.expiration_date else ""),
            "updated_date": str(w.updated_date[0]) if isinstance(w.updated_date, list) and w.updated_date else (
                str(w.updated_date) if w.updated_date else ""),
            "name_servers": w.name_servers or [],
            "status": w.status or [],
            "dnssec": w.dnssec or "",
        }
    except Exception as e:
        log.warning("whois lookup for %s failed: %s", domain, e)
        # Fallback: try system whois command
        out = _run(["whois", domain], timeout=15)
        if out:
            return {"raw_whois": out[:3000], "note": "parsed via system whois"}
        return {}


# ─── SSL/TLS certificate ─────────────────────────────────────────────────


def _ssl_info(domain: str, port: int = 443) -> dict:
    """Fetch SSL/TLS certificate info for a domain."""
    result = {}
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        with ctx.wrap_socket(socket.socket(), server_hostname=domain) as s:
            s.settimeout(10)
            s.connect((domain, port))
            cert = s.getpeercert(binary_form=True)
            if cert:
                from cryptography import x509
                from cryptography.hazmat.backends import default_backend
                cert_obj = x509.load_der_x509_certificate(cert, default_backend())
                issuer = cert_obj.issuer.rfc4514_string()
                subject = cert_obj.subject.rfc4514_string()
                serial = cert_obj.serial_number
                from datetime import timezone
                nb = cert_obj.not_valid_before_utc if hasattr(cert_obj, 'not_valid_before_utc') else cert_obj.not_valid_before.replace(tzinfo=timezone.utc)
                na = cert_obj.not_valid_after_utc if hasattr(cert_obj, 'not_valid_after_utc') else cert_obj.not_valid_after.replace(tzinfo=timezone.utc)
                result = {
                    "subject": subject,
                    "issuer": issuer,
                    "serial": str(serial),
                    "valid_from": nb.isoformat(),
                    "valid_to": na.isoformat(),
                    "days_remaining": (na - nb).days,
                }
                # Get SANs
                try:
                    from cryptography.x509 import SubjectAlternativeName, DNSName
                    san_ext = cert_obj.extensions.get_extension_for_class(SubjectAlternativeName)
                    result["sans"] = [str(name.value) for name in san_ext.value]
                except Exception:
                    result["sans"] = []
                # Check if expired
                from datetime import datetime, timezone
                now = datetime.now(timezone.utc)
                result["expired"] = cert_obj.not_valid_after_utc < now if hasattr(cert_obj, 'not_valid_after_utc') else False
    except ImportError:
        log.warning("cryptography not available, falling back to openssl s_client")
        out = _run(["openssl", "s_client", "-connect", f"{domain}:{port}", "-servername", domain],
                   timeout=15)
        if out:
            # Extract basic cert info from openssl output
            result["raw_openssl"] = out[:2000]
    except Exception as e:
        log.warning("ssl cert fetch for %s failed: %s", domain, e)
    return result


# ─── HTTP headers ──────────────────────────────────────────────────────────


def _http_headers(domain: str) -> dict:
    """Fetch HTTP response headers (security posture)."""
    for proto in ("https", "http"):
        url = f"{proto}://{domain}/"
        try:
            import httpx
            with httpx.Client(timeout=10, follow_redirects=True, verify=False) as client:
                resp = client.get(url)
                headers = dict(resp.headers)
                return {
                    "status_code": resp.status_code,
                    "final_url": str(resp.url),
                    "server": headers.get("server", ""),
                    "content_type": headers.get("content-type", ""),
                    "security_headers": {
                        "strict_transport_security": headers.get("strict-transport-security", ""),
                        "x_frame_options": headers.get("x-frame-options", ""),
                        "x_content_type_options": headers.get("x-content-type-options", ""),
                        "content_security_policy": headers.get("content-security-policy", ""),
                        "x_xss_protection": headers.get("x-xss-protection", ""),
                        "referrer_policy": headers.get("referrer-policy", ""),
                    },
                    "redirect_count": len(resp.history),
                }
        except Exception as e:
            log.debug("http %s failed: %s", url, e)
    return {}


# ─── Main entry point ─────────────────────────────────────────────────────


def domain_info(domain_raw: str) -> dict:
    """Full domain intelligence: DNS, WHOIS, SSL, HTTP headers.

    Returns a dict with keys: domain, dns, whois, ssl, http_headers, error.
    """
    domain = _clean_domain(domain_raw)
    if not domain:
        return {"error": f"invalid domain: {domain_raw}"}

    start = time.time()
    result: dict = {"domain": domain}

    # Resolve IP first
    try:
        result["resolved_ip"] = socket.getaddrinfo(domain, 80)[0][4][0]
    except Exception:
        result["resolved_ip"] = ""

    # Gather data in parallel (sequential here, but each call is fast)
    result["dns"] = _dns_lookup(domain)
    result["whois"] = _whois_lookup(domain)
    result["ssl"] = _ssl_info(domain)
    result["http_headers"] = _http_headers(domain)

    result["lookup_time_ms"] = int((time.time() - start) * 1000)
    return result