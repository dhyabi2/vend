"""
HTML table extraction to structured JSON for Vend.

Fetches a public URL and returns the HTML tables on the page as JSON: each
table becomes a dict with a `headers` row (from <th> or the first <tr>) and a
`rows` list of dicts keyed by column. A data/scraping/research agent pulling
comparison tables, price lists, schedules or statistics gets clean structured
rows in one paid call instead of re-parsing HTML.

Law L65/L66 (ledger block 50):
- L65: The /api/v1/table endpoint is advertised on every surface a buyer reads
  at 0.0001 XNO on nano:mainnet with the single treasury account, and answers
  a bare probe with the 402 challenge.
- L66: A valid table call returns the page's tables as structured rows with
  headers, and malformed input or an unfetchable URL is refused with an error
  rather than an exception.
Only public content is returned; no login, no cookies, no buyer data.
"""

import re
from typing import List, Optional

import httpx
import lxml.html

DEFAULT_TIMEOUT = 15
MAX_TABLES = 10
MAX_ROWS = 200
MAX_CELL_CHARS = 1000


def _text(el) -> str:
    return " ".join((el.text_content() or "").split())


def _parse_table(table) -> dict:
    """Return {headers, rows} for one lxml <table> element."""
    rows_el = table.xpath(".//tr")
    if not rows_el:
        return {"headers": [], "rows": []}
    # Header: any <th> cells, else first row.
    headers = []
    raw_rows = []
    for tr in rows_el:
        ths = tr.xpath(".//th")
        tds = tr.xpath(".//td")
        if ths and not headers:
            headers = [_text(th) for th in ths]
            if not tds:
                continue  # pure header row; skip as a data row
        if tds:
            raw_rows.append([_text(td) for td in tds])

    if not headers:
        # fall back to first data row width as column labels
        if raw_rows:
            headers = [f"col{i+1}" for i in range(len(raw_rows[0]))]
        else:
            headers = []

    # normalize rows to header count
    ncols = len(headers)
    out_rows = []
    for cells in raw_rows[:MAX_ROWS]:
        padded = (cells + [""] * ncols)[:ncols] if ncols else cells
        row = {}
        for j, h in enumerate(headers):
            row[h] = (padded[j] if j < len(padded) else "")[:MAX_CELL_CHARS]
        out_rows.append(row)
    return {"headers": headers, "rows": out_rows}


def tables_for_url(url: str, timeout: int = DEFAULT_TIMEOUT) -> dict:
    """Fetch `url`, parse all HTML tables, return them as structured JSON.

    Never raises. Returns keys: url, count, tables, error (on failure).
    """
    result = {"url": url, "count": 0, "tables": [], "error": None}

    if not url or not url.startswith(("http://", "https://")):
        result["error"] = "invalid_url: must start with http:// or https://"
        return result

    headers = {
        "User-Agent": "Vend/0.1 (Nano pay-per-call API; paypercall.dev)/table",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
    try:
        resp = httpx.get(url, headers=headers, timeout=timeout, follow_redirects=True)
    except httpx.TimeoutException:
        result["error"] = f"timeout fetching {url} (limit: {timeout}s)"
        return result
    except httpx.RequestError as e:
        result["error"] = f"request_failed: {str(e)[:100]}"
        return result

    if resp.status_code != 200:
        result["error"] = f"http_{resp.status_code} fetching {url}"
        return result
    html = resp.text
    if not html or len(html) < 50:
        result["error"] = "empty_or_too_small_response"
        return result

    try:
        doc = lxml.html.document_fromstring(html)
        tables_el = doc.xpath(".//table")[:MAX_TABLES]
    except Exception as e:
        result["error"] = f"parse_error: {str(e)[:100]}"
        return result

    tables = [_parse_table(t) for t in tables_el]
    result["tables"] = tables
    result["count"] = len(tables)
    return result
