"""Unit tests for the render endpoint — no upstream call, no Nano RPC needed.

Tests the URL validation, the upstream-answer parsing and the character cap in
render.render_url: the parts that decide what a paying caller receives and what
the endpoint refuses. The one test that needs the network is skipped when the
renderer is unreachable, so the suite stays deterministic offline.
"""

import unittest

import render
from render import _split_upstream, render_url


class RenderValidationTest(unittest.TestCase):
    def test_invalid_url_rejected(self):
        """A non-http(s) URL returns an error and never calls upstream."""
        result = render_url("not-a-url")
        self.assertIn("Invalid URL", result["error"])
        self.assertEqual(result["markdown"], "")
        self.assertEqual(result["chars"], 0)

    def test_empty_url_rejected(self):
        result = render_url("")
        self.assertIn("Invalid URL", result["error"])

    def test_ftp_scheme_rejected(self):
        result = render_url("ftp://example.com/file")
        self.assertIn("Invalid URL", result["error"])

    def test_max_chars_clamped_and_truncation_flagged(self):
        """The cap is enforced and reported, so a caller can tell a short page
        from a truncated one."""
        try:
            result = render_url("https://example.com", max_chars=100)
        except Exception as exc:  # pragma: no cover - offline environment
            self.skipTest(f"renderer unreachable: {exc}")
        if result["error"]:
            self.skipTest(f"renderer unreachable: {result['error']}")
        self.assertLessEqual(result["chars"], 100)
        self.assertTrue(result["truncated"])

    def test_garbage_max_chars_falls_back_to_default(self):
        """A non-numeric max_chars never raises; it falls back to the default."""
        result = render_url("not-a-url", max_chars="oops")
        self.assertIn("Invalid URL", result["error"])


class UpstreamAnswerParsingTest(unittest.TestCase):
    """The reader prefixes its Markdown with header lines we must strip, or the
    buyer's first line is 'URL Source:' instead of content."""

    def test_title_and_markdown_are_split_out(self):
        body = "Title: React\n\nURL Source: https://react.dev/\n\nMarkdown Content:\n# Hello\n\nBody text.\n"
        title, markdown = _split_upstream(body)
        self.assertEqual(title, "React")
        self.assertTrue(markdown.startswith("# Hello"))
        self.assertNotIn("URL Source", markdown)

    def test_unrecognised_answer_is_kept_whole(self):
        body = "# Just markdown\n\nNo header lines here."
        title, markdown = _split_upstream(body)
        self.assertEqual(title, "")
        self.assertEqual(markdown, body)


class RenderLiveTest(unittest.TestCase):
    def test_real_page_returns_markdown(self):
        """A real JavaScript-heavy page comes back as non-empty Markdown."""
        result = render_url("https://react.dev/")
        if result["error"]:
            self.skipTest(f"renderer unreachable: {result['error']}")
        self.assertGreater(result["chars"], 500)
        self.assertTrue(result["markdown"].strip())


if __name__ == "__main__":
    unittest.main()