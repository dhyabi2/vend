"""Unit tests for the screenshot endpoint — no upstream API, no Nano RPC needed.

Tests the input-validation and dimension-clamping logic in screenshot.capture_screenshot
that run before (and independent of) the upstream webshot.site call, so a real network
request is never made and tests are deterministic.
"""

import unittest

from screenshot import capture_screenshot


class CaptureScreenshotValidationTest(unittest.TestCase):
    def test_invalid_url_rejected(self):
        """A non-http(s) URL returns an error and does not call upstream."""
        result = capture_screenshot("not-a-url")
        self.assertIn("Invalid URL", result["error"])
        self.assertEqual(result["image"], "")

    def test_empty_url_rejected(self):
        result = capture_screenshot("")
        self.assertIn("Invalid URL", result["error"])

    def test_min_dimension_clamped_to_supported_range(self):
        """Dimensions below webshot's supported floor are clamped (320x240)."""
        result = capture_screenshot("https://example.com", width=10, height=10)
        self.assertEqual(result["width"], 320)
        self.assertEqual(result["height"], 240)

    def test_max_dimension_clamped_to_supported_range(self):
        """Dimensions above webshot's supported ceiling are clamped (3840x2160)."""
        result = capture_screenshot("https://example.com", width=5000, height=5000)
        self.assertEqual(result["width"], 3840)
        self.assertEqual(result["height"], 2160)


if __name__ == "__main__":
    unittest.main()
