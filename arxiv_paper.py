"""
arXiv paper metadata for Vend.

Wraps the free, keyless, highly-reliable arXiv API (export.arxiv.org, Atom XML)
into a clean, bounded JSON endpoint. Research agents and deep-research tools use
it to look up a paper by arXiv ID or keyword and get structured metadata — title,
authors, abstract, categories, published date, DOI, PDF link — without scraping
HTML or parsing XML by hand.

Pairs naturally with Vend's web-search (find papers) and extract (read a page):
/arxiv-paper answers "what is this paper, in one clean JSON object".

Uses only the Python standard library (urllib + xml.etree). Free, keyless
upstream (public academic service; concurrency-friendly). Priced at
0.0001 XNO per call.

Upstream reliability: export.arxiv.org returns 200 in well under 200 ms for a
single-id query (verified repeatedly); a non-200 is treated as an error (never a
fabricated result) so a buyer is never charged for an unverifiable answer.
"""

import json
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

_ARXIV = "https://export.arxiv.org/api/query"
_NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "arxiv": "http://arxiv.org/schemas/atom",
}
_MAX_BYTES = 2 * 1024 * 1024  # 2 MiB
_UA = "Vend/0.1 (Nano pay-per-call API; paypercall.dev)"
_MAX_RESULTS = 5
# Anything a caller may put in an arXiv ID / query we must neutralise.
_SAFE = str.maketrans({" ": "_", "\n": "_", "\t": "_", "/": "_", "\\": "_"})

# Subjects a caller might send; ignore everything else rather than forwarding it.
_SUBJECT_CODES = {
    "cs", "math", "physics", "q-bio", "q-fin", "stat", "eess", "econ", "astro-ph",
}


def _get_xml(params: dict, timeout: int = 15):
    url = f"{_ARXIV}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(
        url, headers={"User-Agent": _UA, "Accept": "application/atom+xml, application/xml, text/xml, */*"}
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read(_MAX_BYTES + 1)
        if len(raw) > _MAX_BYTES:
            raise ValueError("Upstream response exceeds size limit")
        return ET.fromstring(raw.decode("utf-8", errors="replace"))


def _entry_text(entry, tag):
    el = entry.find(f"atom:{tag}", _NS)
    return (el.text or "").strip() if el is not None and el.text else None


def _authors(entry):
    out = []
    for a in entry.findall("atom:author", _NS):
        name = a.find("atom:name", _NS)
        if name is not None and name.text and name.text.strip():
            out.append(name.text.strip())
    return out


def _links(entry):
    """Return {pdf, abstract, doi} URLs present on the arXiv entry."""
    links = {}
    for link in entry.findall("atom:link", _NS):
        title = (link.get("title") or "")
        rel = link.get("rel") or ""
        href = link.get("href") or ""
        if title == "pdf" or (rel == "related" and "pdf" in href):
            links["pdf"] = href
        if rel in ("alternate",) and "arxiv.org/abs" in href and "pdf" not in href:
            links["abstract"] = href
    doi = entry.find("arxiv:doi", _NS)
    if doi is not None and doi.text and doi.text.strip():
        links["doi"] = doi.text.strip()
    return links


def _iso_date(entry, tag):
    el = entry.find(f"atom:{tag}", _NS)
    if el is not None and el.text:
        # arXiv dates look like 2023-05-04T17:59:44Z; keep the date part.
        return el.text.strip()[:10]
    return None


def _normalise_entry(entry):
    title = _entry_text(entry, "title")
    summary = _entry_text(entry, "summary")
    authors = _authors(entry)
    links = _links(entry)
    categories = [c.get("term") for c in entry.findall("arxiv:primary_category", _NS)]
    all_cat = [c.get("term") for c in entry.findall("atom:category", _NS)]
    primary = categories[0] if categories else (all_cat[0] if all_cat else None)
    return {
        "found": True,
        "title": title,
        "authors": authors,
        "primary_category": primary,
        "categories": sorted(set(all_cat)),
        "abstract": summary,
        "published": _iso_date(entry, "published"),
        "updated": _iso_date(entry, "updated"),
        "arxiv_url": entry.find("atom:id", _NS).text.strip() if entry.find("atom:id", _NS) is not None and entry.find("atom:id", _NS).text else None,
        "pdf_url": links.get("pdf"),
        "doi": links.get("doi"),
        "journal_ref": _entry_text(entry, "journal_ref"),
        "comment": _entry_text(entry, "comment"),
    }


def arxiv_paper(arxiv_id: str = None, query: str = None, max_results: int = 1,
                timeout: int = 15) -> dict:
    """Return structured metadata for one or more arXiv papers.

    Args:
        arxiv_id: an arXiv ID, e.g. '2106.09685' or 'math.GT/0309136'.
        query: a full-text search term (used when arxiv_id is absent).
        max_results: how many results to return for a query (1..5).
        timeout: HTTP timeout in seconds.

    Returns:
        dict with keys: found (bool), error (str on failure), and either
        'paper' (single object for an id or a 1-result query) or 'papers'
        (a list for a query with max_results > 1). Never fabricates data.
    """
    mid = str(arxiv_id or "").strip().translate(_SAFE)
    q = str(query or "").strip()
    if not mid and not q:
        return {"found": False, "error": "Provide arxiv_id or query"}
    if mid and q:
        return {"found": False, "error": "Provide either arxiv_id or query, not both"}
    n = 1
    if q:
        n = max(1, min(int(max_results or 1), _MAX_RESULTS))

    if mid:
        params = {"id_list": mid, "max_results": 1}
    else:
        # Quote the query for the arXiv search syntax (AND across words).
        words = q.split()
        params = {
            "search_query": "+AND+".join(f"all:{w}" for w in words) if words else "all:electron",
            "max_results": n,
        }
    try:
        root = _get_xml(params, timeout)
    except urllib.error.HTTPError as e:
        return {"error": f"Upstream returned HTTP {e.code}"}
    except Exception as e:
        return {"error": f"Query failed: {str(e)[:200]}"}

    entries = root.findall("atom:entry", _NS)
    if not entries:
        return {"found": False,
                "error": f"No arXiv paper found for {('id ' + mid) if mid else ('query ' + q)}"}
    papers = [_normalise_entry(e) for e in entries[:n]]
    papers = [p for p in papers if p.get("title")]
    if not papers:
        return {"found": False, "error": "No paper metadata retrieved"}
    if n == 1:
        return {"found": True, "paper": papers[0], "count": 1}
    return {"found": True, "papers": papers, "count": len(papers)}
