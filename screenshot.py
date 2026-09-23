"""
Screenshot capture using webshot.site — free, no API key needed.

Captures a full-page or viewport screenshot of any public URL as a PNG
image using headless Chrome rendering (Puppeteer). Uses webshot.site's
free tier as the upstream — no API key, no account needed.

Returns a base64-encoded PNG data URL so agents receive the image inline
without a second fetch.

Priced at 0.0005 XNO per call (premium tier — requires browser rendering).
"""

import logging
import base64
import time
import httpx

log = logging.getLogger("vend.screenshot")

UPSTREAM_URL = "https://webshot.site/api/capture"
UPSTREAM_TIMEOUT = 30  # screenshot rendering can take 10-20s


def capture_screenshot(
    url: str,
    format: str = "png",
    full_page: bool = True,
    width: int = 1280,
    height: int = 720,
) -> dict:
    """Capture a screenshot of a public URL.

    Uses webshot.site's free no-key API (same engine as webshot.site).
    Returns a JSON dict with the screenshot as a base64 data URL, plus
    metadata.

    Args:
        url: The public URL to capture (http:// or https://).
        format: Image format ("png" or "jpeg"). Default "png".
        full_page: If True, capture the entire scrollable document.
        width: Viewport width in pixels (320-3840).
        height: Viewport height in pixels (240-2160).

    Returns:
        dict with keys: url, image (base64 data URL), format, full_page,
        width, height, upstream_time_ms, error
    """
    result = {
        "url": url,
        "image": "",
        "format": format,
        "full_page": full_page,
        "width": width,
        "height": height,
        "upstream_time_ms": 0,
        "error": None,
    }

    if not url or not url.startswith(("http://", "https://")):
        result["error"] = "Invalid URL: must start with http:// or https://"
        return result

    # Clamp dimensions to webshot's supported range
    width = max(320, min(3840, width))
    height = max(240, min(2160, height))
    result["width"] = width
    result["height"] = height

    payload = {
        "url": url,
        "format": format,
        "full_page": full_page,
        "width": width,
        "height": height,
    }

    try:
        start = time.monotonic()
        resp = httpx.post(
            UPSTREAM_URL,
            json=payload,
            timeout=UPSTREAM_TIMEOUT,
        )
        elapsed_ms = int((time.monotonic() - start) * 1000)
        result["upstream_time_ms"] = elapsed_ms

        if resp.status_code != 200:
            result["error"] = (
                f"Upstream returned HTTP {resp.status_code}"
            )
            return result

        # The response body is the raw image bytes
        image_bytes = resp.content
        if not image_bytes or len(image_bytes) < 100:
            result["error"] = "Upstream returned empty image"
            return result

        # Encode as base64 data URL
        mime = "image/png" if format == "png" else "image/jpeg"
        b64 = base64.b64encode(image_bytes).decode("ascii")
        result["image"] = f"data:{mime};base64,{b64}"
        result["image_bytes"] = len(image_bytes)

    except httpx.TimeoutException:
        result["error"] = (
            f"Upstream timeout (limit: {UPSTREAM_TIMEOUT}s)"
        )
    except httpx.RequestError as e:
        result["error"] = f"Upstream request failed: {str(e)[:100]}"
    except Exception as e:
        result["error"] = f"Screenshot error: {str(e)[:100]}"

    return result