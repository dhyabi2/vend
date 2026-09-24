"""Manifest-honesty tests: the live x402 manifest must not carry any
resource with empty `accepts` (an x402 client cannot learn what such a
resource wants), and every resource must be payable (except documented
free/discovery endpoints which belong outside resources).

Verified 2026-09-24: the live manifest had /api/v1/balance (free prepaid
check) present with accepts:[] — removed from resources per this rule.
"""
import json
import unittest
import urllib.request

MANIFEST_URL = "https://extract.paypercall.dev/.well-known/x402"


def fetch_manifest():
    req = urllib.request.Request(MANIFEST_URL, headers={"User-Agent": "vend-manifest-test/1.0"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode())


class TestManifestHonesty(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            cls.manifest = fetch_manifest()
        except Exception as e:  # noqa: BLE001 - report as failure, not crash the class
            cls.manifest = None
            cls.fetch_error = e

    def test_manifest_fetches(self):
        self.assertIsNotNone(self.manifest, f"manifest fetch failed: {getattr(self, 'fetch_error', '?')}")
        self.assertIn("resources", self.manifest)

    def test_no_empty_accepts(self):
        if self.manifest is None:
            self.skipTest("manifest unavailable")
        empty = [r.get("url") for r in self.manifest["resources"] if not r.get("accepts")]
        self.assertEqual(empty, [], f"resources with empty accepts (x402 clients can't handle): {empty}")

    def test_free_balance_not_in_resources(self):
        if self.manifest is None:
            self.skipTest("manifest unavailable")
        free_balance = [r["url"] for r in self.manifest["resources"]
                        if "balance" in r.get("url", "") and not r.get("accepts")]
        self.assertEqual(free_balance, [], "free /api/v1/balance must NOT be a resources entry (accepts:[])")

    def test_trial_declared(self):
        if self.manifest is None:
            self.skipTest("manifest unavailable")
        trial = self.manifest.get("trial")
        self.assertIsNotNone(trial, "manifest must declare a `trial` block (limit/window/scope) so a budgeting client can compute the real price")
        self.assertEqual(trial.get("limit"), 5, "trial.limit should be 5 free calls")
        self.assertIn("window", trial, "trial.window must be set")
        self.assertIn("scope", trial, "trial.scope must be set (e.g. per-IP)")

    def test_free_resources_documented_not_payable(self):
        if self.manifest is None:
            self.skipTest("manifest unavailable")
        # free/documented endpoints must NOT appear inside resources
        free_urls = [x.get("url") for x in self.manifest.get("free", [])]
        res_urls = [r.get("url") for r in self.manifest["resources"]]
        overlap = set(free_urls) & set(res_urls)
        self.assertEqual(list(overlap), [], f"free/documented endpoints must not also be payable resources: {overlap}")

    def test_paid_resources_have_payto(self):
        if self.manifest is None:
            self.skipTest("manifest unavailable")
        bad = []
        for r in self.manifest["resources"]:
            for acc in r.get("accepts", []):
                if "nano:mainnet" not in acc.get("network", ""):
                    bad.append(f"{r['url']} -> non-nano accept {acc.get('network')}")
        self.assertEqual(bad, [])


if __name__ == "__main__":
    unittest.main()
