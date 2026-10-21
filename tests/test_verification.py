import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from contextguard.schemas import FindingStatus, ReviewFinding
from contextguard.verification import VerificationResult


class TestVerificationResult(unittest.TestCase):
    def setUp(self):
        self.finding = ReviewFinding(
            title="Possible bug",
            description="A possible issue",
            file_path="app.py",
        )

    def test_kept_finding_is_actionable(self):
        result = VerificationResult(
            finding=self.finding,
            status=FindingStatus.KEEP,
            reason="Supported by evidence",
            evidence=["test_example.py"],
        )
        self.assertTrue(result.is_actionable())

    def test_filtered_finding_is_not_actionable(self):
        result = VerificationResult(
            finding=self.finding,
            status=FindingStatus.FILTER,
            reason="Not supported",
        )
        self.assertFalse(result.is_actionable())

    def test_uncertain_finding_is_not_actionable(self):
        result = VerificationResult(
            finding=self.finding,
            status=FindingStatus.UNCERTAIN,
            reason="Insufficient evidence",
        )
        self.assertFalse(result.is_actionable())


if __name__ == "__main__":
    unittest.main()
