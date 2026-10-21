import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from contextguard.engine import verify_finding
from contextguard.schemas import FindingStatus, ReviewFinding


class TestVerificationEngine(unittest.TestCase):
    def make_finding(self, confidence, evidence=None):
        return ReviewFinding(
            title="Possible bug",
            description="Potential null handling issue",
            file_path="app.py",
            confidence=confidence,
            evidence=evidence or [],
        )

    def test_keeps_high_confidence_finding_with_evidence(self):
        finding = self.make_finding(0.9, ["test_null.py"])
        result = verify_finding(finding)

        self.assertEqual(result.status, FindingStatus.KEEP)
        self.assertEqual(result.evidence, ["test_null.py"])

    def test_missing_evidence_remains_uncertain(self):
        result = verify_finding(self.make_finding(0.9))
        self.assertEqual(result.status, FindingStatus.UNCERTAIN)

    def test_low_confidence_remains_uncertain(self):
        result = verify_finding(self.make_finding(0.4, ["test_null.py"]))
        self.assertEqual(result.status, FindingStatus.UNCERTAIN)

    def test_invalid_threshold_raises_error(self):
        with self.assertRaises(ValueError):
            verify_finding(self.make_finding(0.9), confidence_threshold=1.5)


if __name__ == "__main__":
    unittest.main()
