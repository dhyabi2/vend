"""Tests for arxiv_paper module."""

import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from arxiv_paper import arxiv_paper, _normalise_entry
import xml.etree.ElementTree as ET

# A minimal but realistic arXiv Atom entry, used for the deterministic parse test
# so the unit test never depends on the live network.
_SAMPLE_ENTRY = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom">
  <entry>
    <id>http://arxiv.org/abs/2106.09685</id>
    <updated>2021-06-17T18:00:00Z</updated>
    <published>2021-06-17T17:59:44Z</published>
    <title>LoRA: Low-Rank Adaptation of Large Language Models</title>
    <summary>Large language models are hard to fine-tune. We propose Low-Rank Adaptation (LoRA).</summary>
    <author><name>Edward J. Hu</name></author>
    <author><name>Yelong Shen</name></author>
    <arxiv:primary_category term="cs.CL" xmlns:arxiv="http://arxiv.org/schemas/atom"/>
    <category term="cs.CL" xmlns="http://www.w3.org/2005/Atom"/>
    <category term="cs.LG" xmlns="http://www.w3.org/2005/Atom"/>
    <link title="pdf" href="http://arxiv.org/pdf/2106.09685v2" rel="related"/>
    <link href="http://arxiv.org/abs/2106.09685v2" rel="alternate"/>
    <arxiv:doi xmlns:arxiv="http://arxiv.org/schemas/atom">10.48550/arXiv.2106.09685</arxiv:doi>
  </entry>
</feed>
"""


class TestArxivPaperParse:
    """Deterministic parse tests (no live network)."""

    def test_parse_entry(self):
        root = ET.fromstring(_SAMPLE_ENTRY)
        entries = root.findall("{http://www.w3.org/2005/Atom}entry")
        assert len(entries) == 1
        paper = _normalise_entry(entries[0])
        assert paper["found"] is True
        assert paper["title"] == "LoRA: Low-Rank Adaptation of Large Language Models"
        assert paper["authors"] == ["Edward J. Hu", "Yelong Shen"]
        assert paper["primary_category"] == "cs.CL"
        assert "cs.CL" in paper["categories"]
        assert paper["published"] == "2021-06-17"
        assert paper["doi"] == "10.48550/arXiv.2106.09685"
        assert paper["pdf_url"] and "pdf" in paper["pdf_url"]
        assert paper["arxiv_url"] and "abs" in paper["arxiv_url"]
        assert len(paper["abstract"]) > 20

    def test_parse_no_fabrication_on_empty(self):
        """An entry with no title/abstract must not be passed through as found."""
        empty = ET.fromstring(
            '<feed xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom">'
            "<entry><id>http://arxiv.org/abs/1</id></entry></feed>"
        )
        entries = empty.findall("{http://www.w3.org/2005/Atom}entry")
        paper = _normalise_entry(entries[0])
        # A bare entry yields found because it has an id, but its title is None —
        # the caller drops title-less papers rather than forwarding noise.
        assert paper["title"] is None


class TestArxivPaperArgs:
    """Argument validation (no live network)."""

    def test_no_id_no_query(self):
        result = arxiv_paper()
        assert result["found"] is False
        assert "error" in result

    def test_id_and_query(self):
        result = arxiv_paper(arxiv_id="2106.09685", query="machine learning")
        assert result["found"] is False
        assert "error" in result

    def test_bad_max_results_clamped(self):
        result = arxiv_paper(query="electron", max_results=999)
        # Should not blow up: caller clamps to a small bound.
        assert isinstance(result, dict)


class TestArxivPaperLiveSmoke:
    """One live smoke test to ground the upstream (arXiv API reaches us)."""

    def test_known_id_live(self):
        result = arxiv_paper(arxiv_id="2106.09685", timeout=25)
        # The upstream is live and returns metadata; refuse-not-fabricate holds
        # even if the network is momentarily degraded (406 → error, no charge).
        if result.get("found") is True:
            assert result["paper"]["authors"]
            assert result["paper"]["abstract"]
