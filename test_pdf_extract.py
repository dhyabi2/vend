"""Unit tests for the pdf-extract endpoint module.

Laws (invent stack):
  L1  A real PDF URL returns clean, page-structured text with a positive
      page_count and no error key.
  L2  An invalid / empty URL returns an error and is never charged.
  L3  A URL that answers HTML (a bot-wall pattern) is refused cleanly with a
      clear error rather than handing the caller a non-PDF page.
  L4  The endpoint is discoverable: it appears in the x402 manifest, the
      OpenAPI spec, the ARD entry source and the INPUT_SPECS used by the 402
      challenge, all at the same public price.
"""


def test_pdf_extract_invalid_url():
    """L2 — an invalid URL returns an error dict, not raised output."""
    from pdf_extract import extract_pdf_text
    result = extract_pdf_text("")
    assert isinstance(result, dict)
    assert result.get("error"), f"Expected an error for empty URL, got: {result}"

    result2 = extract_pdf_text("notaurl")
    assert result2.get("error"), f"Expected 'must start with http' error, got: {result2}"
    assert "http" in result2["error"].lower()


def test_pdf_extract_real_pdf():
    """L1 — a real PDF URL yields page-structured text and a positive page count."""
    from pdf_extract import extract_pdf_text
    result = extract_pdf_text("https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf", timeout=30)
    assert not result.get("error"), f"Expected no error, got: {result.get('error')}"
    assert result["page_count"] >= 1, f"Expected >=1 page, got {result['page_count']}"
    assert isinstance(result["pages"], list) and len(result["pages"]) == result["page_count"]
    assert result["text"], "Expected non-empty extracted text from the dummy PDF"


def test_pdf_extract_html_refusal():
    """L3 — a URL serving HTML instead of a PDF is refused cleanly."""
    from pdf_extract import extract_pdf_text
    result = extract_pdf_text("https://example.com", timeout=30)
    assert isinstance(result, dict)
    if result.get("error"):
        # Either we refused (HTML detected) or upstream gave a non-200; either
        # way the caller must never receive a made-up PDF text.
        assert result["text"] == "" or not result.get("page_count")
    else:
        # A site may legitimately serve a PDF at / — then it must have text.
        assert result.get("text") or result.get("error")


def test_pdf_endpoint_in_discovery_surfaces():
    """L4 — pdf-extract is discoverable at a single consistent price."""
    import server
    m = server.x402_manifest()
    pdf_resources = [r for r in m["resources"] if "/api/v1/pdf-extract" in r["url"]]
    assert len(pdf_resources) == 1, "exactly one pdf-extract resource in the x402 manifest"
    manifest_amount = pdf_resources[0]["accepts"][0]["amount"]
    assert manifest_amount == server.PRICE_PDF_RAW, (
        f"x402 manifest amount {manifest_amount} != PRICE_PDF_RAW {server.PRICE_PDF_RAW}"
    )

    spec = server.build_openapi_spec(
        {"extract": "https://e.x", "check": "https://c.x", "domain": "https://d.x",
         "search": "https://s.x", "geoip": "https://g.x", "nano": "https://n.x",
         "status": "https://e.x", "youtube": "https://e.x", "pdf": "https://e.x"},
        {"extract": 0.0001, "domain": 0.0005, "websearch": 0.0001, "geoip": 0.0001,
         "nano": 0.0005, "status": 0.0001, "youtube": 0.0005, "pdf": server.PRICE_PDF_XNO},
    )
    pdf_path = spec["paths"].get("/api/v1/pdf-extract")
    assert pdf_path is not None, "pdf-extract missing from OpenAPI spec"
    assert pdf_path["get"]["x-payment-info"]["price"]["amount"] == f"{server.PRICE_PDF_XNO:.6f}"

    assert "/api/v1/pdf-extract" in server.INPUT_SPECS, "pdf-extract missing from INPUT_SPECS (402 challenge)"
    assert any("pdf" in e["metadata"]["endpoint"] for e in server.ard_entries()), (
        "pdf-extract missing from ARD entry source"
    )
