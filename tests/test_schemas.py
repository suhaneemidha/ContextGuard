import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from contextguard.schemas import FindingStatus, ReviewFinding


class TestReviewFinding(unittest.TestCase):
    def test_default_values(self):
        finding = ReviewFinding(
            title="Example issue",
            description="Example description",
            file_path="app.py",
        )

        self.assertEqual(finding.status, FindingStatus.UNCERTAIN)
        self.assertEqual(finding.confidence, 0.0)
        self.assertEqual(finding.evidence, [])

    def test_finding_can_be_kept(self):
        finding = ReviewFinding(
            title="Example issue",
            description="Example description",
            file_path="app.py",
            status=FindingStatus.KEEP,
        )

        self.assertEqual(finding.status, FindingStatus.KEEP)


if __name__ == "__main__":
    unittest.main()
