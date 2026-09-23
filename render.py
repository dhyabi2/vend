"""
JavaScript-rendered page to clean text, for scraping and research agents.

The plain /api/v1/extract endpoint fetches a URL over HTTP and parses the
returned HTML. For a page whose content is produced by JavaScript in the
browser (SPAs, Next.js/React sites, dashboards, search results), that HTML is
an empty shell and extract returns little or nothing.

This module answers that case: it asks a rendering reader (r.jina.ai, free,
no API key) to execute the page in a real browser and return the rendered
content as Markdown, then hands back a stable JSON shape with the title, the
Markdown and the character count.

Priced at 0.0005 XNO per call (premium tier - requires browser rendering).

The module never raises for bad input or an upstream failure: it returns a
dict with a populated ``error`` field instead, so the paid-call path can
report the failure honestly rather than losing the caller's block.
"""

import logging
import time

import httpx

log = logging.getLogger("vend.render")

# r.jina.ai is a free, keyless rendering reader: it loads the URL in a real
# browser and returns the rendered content as Markdown. No account, no key.
UPSTREAM_URL = "https://r.jina.ai/"
UPSTREAM_TIMEOUT = 30  # browser rendering of a heavy page can take 10-25s
USER_AGENT = "Vend/0.1 (Nano pay-per-call API; paypercall.dev)"

# Guard the response size we echo back to the caller.
MAX_CHARS_DEFAULT = 200_000
MAX_CHARS_CEILING = 500_000


def _split_upstream(body: str) -> tuple[str, str]:
    """Split the reader's answer into (title, markdown).

    The reader prefixes its Markdown with header lines:

        Title: <page title>

        URL Source: <url>

        Markdown Content:
        <the markdown>

    Anything that does not match that shape is returned whole as the
    Markdown, with an empty title, rather than being thrown away.
    """
    title = ""
    markdown = body

    if body.startswith("Title:"):
        head, _, rest = body.partition("\n")
        title = head[len("Title:"):].strip()
        markdown = rest

    marker = "Markdown Content:"
    if marker in markdown:
        markdown = markdown.split(marker, 1)[1]

    return title, markdown.lstrip("\n")


def render_url(url: str, max_chars: int = MAX_CHARS_DEFAULT) -> dict:
    """Render a public URL in a browser and return its content as Markdown.

    Args:
        url: The public URL to render (http:// or https://).
        max_chars: Cap on the Markdown returned, 100 .. 500000.

    Returns:
        dict with keys: url, title, markdown, chars, truncated,
        upstream_time_ms, error
    """
    result = {
        "url": url,
        "title": "",
        "markdown": "",
        "chars": 0,
        "truncated": False,
        "upstream_time_ms": 0,
        "error": None,
    }

    if not url or not url.startswith(("http://", "https://")):
        result["error"] = "Invalid URL: must start with http:// or https://"
        return result

    try:
        max_chars = int(max_chars)
    except (TypeError, ValueError):
        max_chars = MAX_CHARS_DEFAULT
    max_chars = max(100, min(MAX_CHARS_CEILING, max_chars))

    try:
        start = time.monotonic()
        resp = httpx.get(
            UPSTREAM_URL + url,
            headers={
                "User-Agent": USER_AGENT,
                "x-respond-with": "markdown",
                "Accept": "text/plain",
            },
            timeout=UPSTREAM_TIMEOUT,
            follow_redirects=True,
        )
        result["upstream_time_ms"] = int((time.monotonic() - start) * 1000)

        if resp.status_code != 200:
            result["error"] = f"HTTP {resp.status_code} rendering {url}"
            return result

        body = resp.text or ""
        if not body.strip():
            result["error"] = "Empty response from the renderer"
            return result

        title, markdown = _split_upstream(body)

        if len(markdown) > max_chars:
            markdown = markdown[:max_chars]
            result["truncated"] = True

        if not markdown.strip():
            result["error"] = "The renderer returned no readable content"
            return result

        result["title"] = title
        result["markdown"] = markdown
        result["chars"] = len(markdown)
        return result

    except Exception as exc:  # network error, timeout, anything upstream
        log.exception("render failed for %s", url)
        result["error"] = f"Render failed: {type(exc).__name__}"
        return result