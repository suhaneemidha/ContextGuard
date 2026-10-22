import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from contextguard.engine import verify_finding
from contextguard.evidence import EvidenceReference
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


class TestStructuredEvidenceVerification(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        source_dir = self.root / "src"
        source_dir.mkdir()
        (source_dir / "auth.py").write_text(
            "def get_user():\n    return user_data\n",
            encoding="utf-8",
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def make_finding(self, confidence=0.9):
        return ReviewFinding(
            title="Possible authorization issue",
            description="The endpoint may expose user data.",
            file_path="src/auth.py",
            confidence=confidence,
        )

    def make_reference(self, excerpt="    return user_data"):
        return EvidenceReference(
            file_path="src/auth.py",
            start_line=2,
            end_line=2,
            excerpt=excerpt,
            explanation="This line returns user data.",
        )

    def test_matching_structured_evidence_is_accepted(self):
        finding = self.make_finding()
        reference = self.make_reference()

        result = verify_finding(
            finding,
            evidence_references=[reference],
            repository_root=self.root,
        )

        self.assertEqual(result.status, FindingStatus.KEEP)
        self.assertEqual(result.evidence_references, [reference])
        self.assertTrue(result.is_actionable())

    def test_mismatched_structured_evidence_is_rejected(self):
        finding = self.make_finding()
        reference = self.make_reference("    return admin_data")

        result = verify_finding(
            finding,
            evidence_references=[reference],
            repository_root=self.root,
        )

        self.assertEqual(result.status, FindingStatus.UNCERTAIN)
        self.assertEqual(result.evidence_references, [])
        self.assertFalse(result.is_actionable())

    def test_structured_evidence_without_repository_root_is_uncertain(self):
        finding = self.make_finding()
        reference = self.make_reference()

        result = verify_finding(finding, evidence_references=[reference])

        self.assertEqual(result.status, FindingStatus.UNCERTAIN)
        self.assertEqual(result.evidence_references, [])
        self.assertIn("repository root", result.reason)

    def test_low_confidence_with_matching_structured_evidence_is_uncertain(self):
        finding = self.make_finding(confidence=0.4)
        reference = self.make_reference()

        result = verify_finding(
            finding,
            evidence_references=[reference],
            repository_root=self.root,
        )

        self.assertEqual(result.status, FindingStatus.UNCERTAIN)
        self.assertEqual(result.evidence_references, [reference])
        self.assertFalse(result.is_actionable())


if __name__ == "__main__":
    unittest.main()
