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


class TestStructuredEvidenceVerification(unittest.TestCase):
    def test_keeps_high_confidence_finding_with_structured_evidence(self):
        from contextguard.evidence import EvidenceReference

        finding = TestVerificationEngine().make_finding(0.9)
        reference = EvidenceReference(
            file_path="src/auth.py",
            start_line=12,
            end_line=12,
            excerpt="return user_data",
            explanation="The data is returned without an authorization check.",
        )

        result = verify_finding(finding, evidence_references=[reference])

        self.assertEqual(result.status, FindingStatus.KEEP)
        self.assertEqual(result.evidence_references, [reference])
        self.assertTrue(result.is_actionable())

    def test_low_confidence_with_structured_evidence_remains_uncertain(self):
        from contextguard.evidence import EvidenceReference

        finding = TestVerificationEngine().make_finding(0.4)
        reference = EvidenceReference(
            file_path="src/auth.py",
            start_line=12,
            end_line=12,
            excerpt="return user_data",
            explanation="The data is returned without an authorization check.",
        )

        result = verify_finding(finding, evidence_references=[reference])

        self.assertEqual(result.status, FindingStatus.UNCERTAIN)
        self.assertEqual(result.evidence_references, [reference])
