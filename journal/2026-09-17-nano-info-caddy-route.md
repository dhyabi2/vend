# 2026-09-17: nano-info Caddy routing + external-readiness (block 16 close-out)

## Context
Block 16 (nano-info endpoint) code was complete and internally verified. The remaining
gap was external reachability: `nano.paypercall.dev` DNS resolved to Vercel IPs
(216.150.16.193), not this box (172.86.112.181), and Caddy did not route the host at all.

## What was done
1. **Caddy admin API**: added `nano.paypercall.dev` to the virtual host matcher that
   reverse-proxies all Vend API subdomains → 127.0.0.1:8402. Before:
   `[extract, check, domain, search, geoip]`; after adds `nano`. Persistent (autosaved to
   `/var/lib/caddy/.config/caddy/autosave.json`).
2. **Verified server**: production server on 127.0.0.1:8402 still healthy; x402 manifest
   has 6 resources including nano-info; nano-info returns 402 without payment.
3. **Docs updated for 6th endpoint**: README endpoint table + conformance list;
   static/landing.html endpoint table; static/vend-directories.json endpoints list
   (5 → 6). llms.txt already had nano-info.

## Still blocked (external)
- `nano.paypercall.dev` A record still points to Vercel IPs. Needs an A record →
  172.86.112.181. Requires domain provider credentials NOT on this box. Until then:
  Caddy will not issue a Let's Encrypt cert (ACME can't verify a host that doesn't
  reach here), so the subdomain is not externally listable.
- Once DNS is fixed, Caddy auto-issues the cert and nano.paypercall.dev goes live
  without further code changes.

## Money
- Treasury: 29.9998 XNO (unchanged)
- Receivable: 0 XNO
- Paid calls: 0 delivered (all time) — the one number that still matters.
