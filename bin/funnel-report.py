#!/usr/bin/env python3
"""Vend funnel report — what strangers actually do with the free door.

Access-log sources, in order of preference:
  1. a real access log file (--log PATH), parsed as JSON lines or common log format;
  2. `journalctl -u vend-api`, where uvicorn logs every request line:
        172.86.112.181:0 - "GET /api/v1/geoip HTTP/1.1" 402 Payment Required

The journal is the source of truth on this box: Caddy writes no access log, and
all public traffic arrives at uvicorn with the real client IP because Caddy sets
X-Forwarded-For. Requests from this box are counted as `internal` and excluded
from the outside funnel.

Usage:
    python3 bin/funnel-report.py [--log PATH] [--journal] [--days N] [--json]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import socket
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

DEFAULT_LOGS = ["/var/log/caddy/access.log", "/var/log/caddy/vend-access.log"]

API_RE = re.compile(r"/api/v1/([a-z0-9-]+)")
UVICORN_RE = re.compile(
    r'(?P<ip>\d{1,3}(?:\.\d{1,3}){3}):\d+ - "'
    r'(?P<method>[A-Z]+) (?P<path>\S+) HTTP/[\d.]+" (?P<status>\d{3})')
SYSLOG_TS_RE = re.compile(r"^(\w{3} +\d+ \d{2}:\d{2}:\d{2})")
ENDPOINTS = {"extract", "check-link", "domain-info", "web-search", "geoip",
             "nano-info", "demo", "status"}
DISCOVERY_PATHS = {"/", "/health", "/llms.txt", "/.well-known/agent.json",
                   "/.well-known/agent-card.json", "/mcp", "/openapi.json",
                   "/.well-known/mcp-registry-auth", "/status",
                   "/.well-known/x402.json", "/robots.txt", "/sitemap.xml"}


def local_ips() -> set[str]:
    ips = {"127.0.0.1", "::1"}
    try:
        ips.update(socket.gethostbyname_ex(socket.gethostname())[2])
    except OSError:
        pass
    v = os.environ.get("VEND_PUBLIC_IP")
    if v:
        ips.add(v)
    return ips


def read_journal(days: int, unit: str = "vend-api") -> list[str]:
    try:
        p = subprocess.run(
            ["journalctl", "-u", unit, "--since", f"-{days}d", "--no-pager", "-o", "short"],
            capture_output=True, text=True, timeout=120)
        return p.stdout.splitlines() if p.returncode == 0 else []
    except (OSError, subprocess.SubprocessError):
        return []


def year_for_month(mon: str) -> int:
    now = datetime.now(timezone.utc)
    month = datetime.strptime(mon, "%b").month
    return now.year - 1 if month > now.month else now.year


def parse_log_file(path: str) -> list[str]:
    with open(path, "r", errors="replace") as fh:
        return fh.readlines()


def event_ts(line: str) -> datetime | None:
    """Timestamp of a journal/CLF line, in UTC, or None when unreadable."""
    stamp = SYSLOG_TS_RE.match(line)
    if stamp:
        try:
            dt = datetime.strptime(stamp.group(1), "%b %d %H:%M:%S")
            return dt.replace(year=year_for_month(dt.strftime("%b")), tzinfo=timezone.utc)
        except ValueError:
            pass
    iso = re.search(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})", line)
    if iso:
        try:
            return datetime.strptime(iso.group(1), "%Y-%m-%d %H:%M:%S").replace(
                tzinfo=timezone.utc)
        except ValueError:
            return None
    clf = re.search(r"\[(\d{2}/\w{3}/\d{4}:\d{2}:\d{2}:\d{2} [+-]\d{4})\]", line)
    if clf:
        try:
            return datetime.strptime(clf.group(1), "%d/%b/%Y:%H:%M:%S %z")
        except ValueError:
            return None
    js = re.search(r'"(?:ts|time|timestamp)"\s*:\s*"([^"]+)"', line)
    if js:
        try:
            return datetime.fromisoformat(js.group(1).replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", default=None, help="access log file (JSON lines or CLF)")
    ap.add_argument("--journal", action="store_true", help="force journalctl source")
    ap.add_argument("--unit", default="vend-api")
    ap.add_argument("--days", type=int, default=7)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    source = ""
    lines: list[str] = []
    if args.log and not args.journal:
        if not os.path.exists(args.log):
            print(f"no such log file: {args.log}", file=sys.stderr)
            return 2
        source = args.log
        lines = parse_log_file(args.log)
    elif not args.journal:
        existing = [p for p in DEFAULT_LOGS if os.path.exists(p)]
        if existing:
            source = existing[0]
            lines = parse_log_file(source)
    if not lines:
        source = f"journalctl -u {args.unit}"
        lines = read_journal(args.days, args.unit)
    if not lines:
        msg = (f"no access source: no {' or '.join(DEFAULT_LOGS)} and no readable "
               f"journal for unit {args.unit}")
        print(json.dumps({"error": msg}) if args.json else msg)
        return 2

    local = local_ips()
    cutoff = datetime.now(timezone.utc) - timedelta(days=args.days)
    by_day: dict[str, Counter] = defaultdict(Counter)
    ips: Counter = Counter()
    uas: Counter = Counter()
    total = internal = 0

    for line in lines:
        m = UVICORN_RE.search(line)
        if not m:
            continue
        ts = event_ts(line)
        if ts is None or ts < cutoff:
            continue
        total += 1
        ip = m.group("ip")
        if ip in local:
            internal += 1
            continue
        path = m.group("path").split("?")[0]
        status = int(m.group("status"))
        c = by_day[ts.strftime("%Y-%m-%d")]
        ep = API_RE.search(path)
        if ep and ep.group(1) in ENDPOINTS:
            c["api_calls"] += 1
            c[f"ep:{ep.group(1)}"] += 1
            if status == 402:
                c["challenged_402"] += 1
            elif status == 200:
                c["served_200"] += 1
            else:
                c[f"status_{status}"] += 1
        elif path in DISCOVERY_PATHS or path.startswith("/.well-known"):
            c["discovery_docs"] += 1
            if status == 404:
                c["docs_404"] += 1
        else:
            c["other"] += 1
        ips[ip] += 1
        ua = re.search(r'"([^"]*(?:curl|bot|agent|python|MCP|LLM|GPT|Claude)[^"]*)"',
                       line, re.I)
        if ua:
            uas[ua.group(1)[:60]] += 1

    outside = total - internal
    out = {
        "source": source,
        "window_days": args.days,
        "lines_scanned": len(lines),
        "requests_total": total,
        "internal_requests": internal,
        "outside_requests": outside,
        "outside_distinct_ips": len(ips),
        "by_day": {d: dict(c) for d, c in sorted(by_day.items())},
        "top_ips": ips.most_common(10),
        "agent_user_agents": uas.most_common(10),
        "settled_money_source": "state/vend.sqlite3 redemptions table",
    }
    if args.json:
        print(json.dumps(out, indent=2))
        return 0

    print(f"source: {source}  window: {args.days}d  scanned {len(lines)} lines")
    print(f"requests {total}  internal {internal}  OUTSIDE {outside}  "
          f"distinct outside IPs {len(ips)}")
    for d in sorted(by_day):
        c = by_day[d]
        print(f"  {d}: outside={sum(c.values())} api={c.get('api_calls', 0)} "
              f"402={c.get('challenged_402', 0)} 200={c.get('served_200', 0)} "
              f"docs={c.get('discovery_docs', 0)} other={c.get('other', 0)}")
        eps = {k[3:]: v for k, v in c.items() if k.startswith("ep:")}
        if eps:
            print("      endpoints:", ", ".join(f"{k}={v}" for k, v in
                                                 sorted(eps.items(), key=lambda kv: -kv[1])))
    if ips:
        print("top outside IPs:", ", ".join(f"{i}({n})" for i, n in ips.most_common(5)))
    return 0


if __name__ == "__main__":
    sys.exit(main())