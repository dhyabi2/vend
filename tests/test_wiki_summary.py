"""Tests for wiki_summary module."""

import json
import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from wiki_summary import wiki_summary


class TestWikiSummary:
    """Tests for the wiki_summary module (unit + one live smoke)."""

    def test_known_entity(self):
        """A well-known Wikipedia article should return a clean profile."""
        result = wiki_summary("Nano (cryptocurrency)", timeout=15)
        assert result["found"] is True
        assert result["title"] == "Nano (cryptocurrency)"
        assert result["wikidata_id"] == "Q47512046"
        assert result["description"] is not None
        assert len(str(result.get("extract"))) > 50
        assert result["url"] is not None
        # Thumbnail is optional — some articles lack one in the summary response
        if result.get("thumbnail"):
            assert "/Nano_" in str(result.get("thumbnail")) or "nano" in str(result.get("thumbnail")).lower()

    def test_known_company(self):
        """Companies should return a profile with a description."""
        result = wiki_summary("OpenAI", timeout=15)
        assert result["found"] is True
        assert result["title"] is not None
        assert len(str(result.get("extract"))) > 50

    def test_unknown_topic(self):
        """A non-existent topic should return found=False with a clear error."""
        result = wiki_summary("qwxyz999_nonexistent_xyz", timeout=15)
        assert result["found"] is False
        assert "No article" in str(result.get("error", ""))

    def test_empty_query(self):
        """Empty query should return found=False without hitting upstream."""
        result = wiki_summary("", timeout=10)
        assert result["found"] is False
        assert "No query" in str(result.get("error", ""))

    def test_none_query(self):
        """None query should return found=False without hitting upstream."""
        result = wiki_summary(None, timeout=10)
        assert result["found"] is False
        assert "No query" in str(result.get("error", ""))

    def test_non_english_lang_refused(self):
        """Only English (en) is served; lang=fr should be refused upfront."""
        result = wiki_summary("Nano", lang="fr", timeout=10)
        assert result["found"] is False
        assert "Only lang=en" in str(result.get("error", ""))

    def test_injection_attempt(self):
        """Path traversal via query should be neutralised."""
        result = wiki_summary("a/b/../../etc", timeout=15)
        # The neutralised query looks up "a_b_.._.._etc" which doesn't exist
        assert result["found"] is False
        assert result["error"] is not None

    def test_output_shape(self):
        """Return dict has the expected stable keys."""
        result = wiki_summary("Python (programming language)", timeout=15)
        assert result["found"] is True
        for key in ("found", "title", "description", "extract", "lang",
                    "wikidata_id", "thumbnail", "url"):
            assert key in result
        # extract_html must never be forwarded
        assert result.get("extract_html") is None

    def test_serializable(self):
        """Result must be JSON-serializable without an encoder."""
        result = wiki_summary("Nano (cryptocurrency)", timeout=15)
        dumped = json.dumps(result)
        assert isinstance(dumped, str)
        assert len(dumped) > 20

    def test_timeout_graceful(self):
        """A very short timeout must return an error, not crash."""
        result = wiki_summary("Nano (cryptocurrency)", timeout=0.001)
        assert "error" in result or not result.get("found")
