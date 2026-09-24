"""
URL-to-clean-text extraction using trafilatura.
Returns machine-readable JSON with extracted content.
"""

from typing import Optional
import trafilatura
import httpx


def extract_url(url: str, timeout: int = 15) -> dict:
    """
    Fetch a URL and extract clean text/markdown.

    Args:
        url: The URL to extract content from
        timeout: HTTP request timeout in seconds

    Returns:
        dict with keys: url, title, text, markdown, error
    """
    result = {
        "url": url,
        "title": "",
        "text": "",
        "markdown": "",
        "error": None
    }

    # Validate URL
    if not url or not url.startswith(("http://", "https://")):
        result["error"] = "Invalid URL: must start with http:// or https://"
        return result

    try:
        # Download the URL content via httpx
        headers = {
            "User-Agent": "Vend/0.1 (Nano pay-per-call API; paypercall.dev)",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
        resp = httpx.get(url, headers=headers, timeout=timeout, follow_redirects=True)

        if resp.status_code != 200:
            result["error"] = f"HTTP {resp.status_code} fetching {url}"
            return result

        html = resp.text
        if not html or len(html) < 50:
            result["error"] = "Empty or too small response"
            return result

        # Extract with trafilatura
        extracted_text = trafilatura.extract(
            html,
            output_format="txt",
            include_links=True,
            include_images=False,
            include_comments=False,
            favor_recall=True,
        )

        extracted_markdown = trafilatura.extract(
            html,
            output_format="markdown",
            include_links=True,
            include_images=False,
            include_comments=False,
            favor_recall=True,
        )

        # Get title via trafilatura metadata
        metadata = trafilatura.extract(html, output_format="json", favor_recall=True)
        title = ""
        if metadata:
            try:
                import json
                meta = json.loads(metadata)
                title = meta.get("title", "")
            except (json.JSONDecodeError, ValueError):
                pass

        # If no title from metadata, try basic HTML parsing
        if not title:
            import re
            title_match = re.search(r'<title[^>]*>(.*?)</title>', html, re.IGNORECASE | re.DOTALL)
            if title_match:
                title = title_match.group(1).strip()

        result["title"] = title or ""
        result["text"] = extracted_text or ""
        result["markdown"] = extracted_markdown or ""

        if not result["text"] and not result["markdown"]:
            result["error"] = "No extractable content found on page"

    except httpx.TimeoutException:
        result["error"] = f"Timeout fetching {url} (limit: {timeout}s)"
    except httpx.RequestError as e:
        result["error"] = f"Request failed: {str(e)[:100]}"
    except Exception as e:
        result["error"] = f"Extraction error: {str(e)[:100]}"

    return result