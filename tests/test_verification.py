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


class TestStructuredVerificationEvidence(unittest.TestCase):
    def test_stores_structured_evidence_references(self):
        from contextguard.evidence import EvidenceReference

        finding = ReviewFinding(
            title="Missing authorization check",
            description="The endpoint may allow unauthorized access.",
            file_path="src/auth.py",
        )
        evidence = EvidenceReference(
            file_path="src/auth.py",
            start_line=12,
            end_line=12,
            excerpt="return user_data",
            explanation="The data is returned without an authorization check.",
        )
        result = VerificationResult(
            finding=finding,
            status=FindingStatus.UNCERTAIN,
            reason="Needs further verification.",
            evidence_references=[evidence],
        )

        self.assertEqual(len(result.evidence_references), 1)
        self.assertEqual(
            result.evidence_references[0].file_path,
            "src/auth.py",
        )
        self.assertFalse(result.is_actionable())

    def test_structured_evidence_defaults_to_empty_list(self):
        finding = ReviewFinding(
            title="Potential issue",
            description="Needs review.",
            file_path="src/app.py",
        )
        result = VerificationResult(
            finding=finding,
            status=FindingStatus.UNCERTAIN,
            reason="Not enough evidence.",
        )

        self.assertEqual(result.evidence_references, [])
