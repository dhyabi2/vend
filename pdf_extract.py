"""
PDF-to-text extraction from a URL.
Agents constantly hit PDF links (papers, specs, reports, invoices) that a normal
web extractor cannot read because the bytes are not HTML. This endpoint fetches
a PDF over HTTP and returns its extracted text with page-level structure, ready
for LLM consumption.
"""

from typing import Optional
import io
import httpx
import pypdf


def extract_pdf_text(url: str, timeout: int = 30) -> dict:
    """
    Fetch a PDF URL and extract its text, preserving page structure.

    Args:
        url: The URL of the PDF to extract
        timeout: HTTP request timeout in seconds

    Returns:
        dict with keys: url, title, text, pages, page_count, error
    """
    result = {
        "url": url,
        "title": "",
        "text": "",
        "pages": [],
        "page_count": 0,
        "error": None,
    }

    # Validate URL
    if not url or not url.startswith(("http://", "https://")):
        result["error"] = "Invalid URL: must start with http:// or https://"
        return result

    try:
        # Download the PDF bytes
        headers = {
            "User-Agent": "Vend/0.1 (Nano pay-per-call API; paypercall.dev)",
            "Accept": "application/pdf,application/octet-stream,*/*",
        }
        resp = httpx.get(url, headers=headers, timeout=timeout, follow_redirects=True)

        if resp.status_code != 200:
            result["error"] = f"HTTP {resp.status_code} fetching {url}"
            return result

        content_type = resp.headers.get("content-type", "").lower()
        body = resp.content

        if not body or len(body) < 20:
            result["error"] = "Empty or too small response"
            return result

        # If the server returned HTML (a common bot-wall pattern), refuse cleanly
        # rather than handing the caller a page that is not a PDF.
        if "html" in content_type or body[:5].lstrip()[:4] == b"<!DO" or b"<html" in body[:1024].lower():
            result["error"] = (
                "URL returned HTML, not a PDF (the site may be blocking programmatic "
                "access). The status/content-type was "
                f"{content_type or 'unknown'}."
            )
            return result

        # Parse with pypdf
        reader = pypdf.PdfReader(io.BytesIO(body))
        page_count = len(reader.pages)
        result["page_count"] = page_count

        # Extract title from document metadata if present
        meta = reader.metadata
        if meta and getattr(meta, "title", None):
            result["title"] = str(meta.title)

        pages = []
        full_text_lines = []
        for i, page in enumerate(reader.pages):
            try:
                page_text = page.extract_text() or ""
            except Exception:
                page_text = ""
            page_text = page_text.strip()
            pages.append(
                {
                    "page": i + 1,
                    "text": page_text,
                }
            )
            if page_text:
                full_text_lines.append(page_text)

        result["pages"] = pages
        result["text"] = "\n\n".join(full_text_lines)

        if not result["text"] and page_count > 0:
            result["error"] = (
                "PDF parsed but contained no extractable text (it may be a "
                "scanned/image-only document)."
            )

        return result

    except pypdf.errors.PdfReadError as e:
        result["error"] = f"Not a valid PDF: {e}"
        return result
    except httpx.HTTPError as e:
        result["error"] = f"HTTP error fetching {url}: {e}"
        return result
    except Exception as e:
        result["error"] = f"Extraction failed: {e}"
        return result
