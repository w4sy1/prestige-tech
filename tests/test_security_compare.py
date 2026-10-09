import unittest

from prestige_core.security_compare import compare_audits


class SecurityCompareTest(unittest.TestCase):
    def test_unknown_coverage_is_not_reported_complete(self):
        before = {"coverage": {"firewall": "UNKNOWN"}, "unknown_checks": 1,
                  "risk_score": 0, "alerts_total": 1}
        after = {"coverage": {"firewall": "EVALUATED"}, "unknown_checks": 0,
                 "risk_score": 15, "alerts_total": 2}
        result = compare_audits(before, after)
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertIn({"check": "firewall", "before": "UNKNOWN", "after": "EVALUATED"},
                      result["coverage_changes"])


if __name__ == "__main__":
    unittest.main()
