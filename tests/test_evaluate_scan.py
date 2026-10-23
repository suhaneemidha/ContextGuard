import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.evaluate_scan import score_findings


class TestBenchmarkScoring(unittest.TestCase):
    def setUp(self):
        self.vulnerable_case = {
            "expect_vulnerability": True,
            "keywords": ("command injection", "shell injection"),
        }
        self.safe_case = {
            "expect_vulnerability": False,
            "keywords": (),
        }

    def finding(self, title, actionable=True, description=""):
        return {
            "title": title,
            "description": description,
            "file_path": "example.py",
            "actionable": actionable,
            "status": "keep" if actionable else "uncertain",
        }

    def test_expected_vulnerability_without_extras_passes(self):
        result = score_findings(
            [self.finding("Command injection via shell command")],
            self.vulnerable_case,
        )
        self.assertTrue(result["passed"])
        self.assertEqual(result["unexpected_actionable_findings"], [])

    def test_unrelated_actionable_finding_fails_vulnerable_case(self):
        findings = [
            self.finding("Command injection via shell command"),
            self.finding("Missing import of subprocess"),
        ]
        result = score_findings(findings, self.vulnerable_case)
        self.assertFalse(result["passed"])
        self.assertTrue(result["expected_issue_detected"])
        self.assertEqual(len(result["unexpected_actionable_findings"]), 1)
        self.assertEqual(
            result["unexpected_actionable_findings"][0]["title"],
            "Missing import of subprocess",
        )

    def test_missing_expected_vulnerability_fails(self):
        result = score_findings(
            [self.finding("Unrelated issue")],
            self.vulnerable_case,
        )
        self.assertFalse(result["passed"])
        self.assertFalse(result["expected_issue_detected"])

    def test_safe_control_with_no_findings_passes(self):
        result = score_findings([], self.safe_case)
        self.assertTrue(result["passed"])
        self.assertEqual(result["actionable_findings"], 0)

    def test_safe_control_with_actionable_finding_fails(self):
        result = score_findings(
            [self.finding("Possible issue")],
            self.safe_case,
        )
        self.assertFalse(result["passed"])
        self.assertEqual(len(result["unexpected_actionable_findings"]), 1)

    def test_uncertain_extra_finding_does_not_count_as_actionable(self):
        result = score_findings(
            [
                self.finding("Command injection"),
                self.finding("Uncertain additional concern", actionable=False),
            ],
            self.vulnerable_case,
        )
        self.assertTrue(result["passed"])
        self.assertEqual(result["uncertain_findings"], 1)


if __name__ == "__main__":
    unittest.main()
