import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from contextguard.evidence import EvidenceReference
from contextguard.evidence_validator import validate_evidence_reference


class TestEvidenceValidator(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.source = self.root / "auth.py"
        self.source.write_text(
            "def get_user():\n    return user_data\n",
            encoding="utf-8",
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_accepts_matching_source_excerpt(self):
        reference = EvidenceReference(
            "auth.py", 2, 2, "    return user_data", "Returns user data."
        )
        self.assertTrue(validate_evidence_reference(self.root, reference))

    def test_rejects_excerpt_that_does_not_match(self):
        reference = EvidenceReference(
            "auth.py", 2, 2, "return admin_data", "Claims admin data is returned."
        )
        self.assertFalse(validate_evidence_reference(self.root, reference))

    def test_rejects_missing_file(self):
        reference = EvidenceReference(
            "missing.py", 1, 1, "return None", "Missing source."
        )
        self.assertFalse(validate_evidence_reference(self.root, reference))

    def test_rejects_line_range_beyond_file(self):
        reference = EvidenceReference(
            "auth.py", 1, 5, "def get_user():", "Invalid range."
        )
        self.assertFalse(validate_evidence_reference(self.root, reference))

    def test_rejects_path_outside_repository(self):
        reference = EvidenceReference(
            "../outside.py", 1, 1, "secret", "Outside repository."
        )
        self.assertFalse(validate_evidence_reference(self.root, reference))


if __name__ == "__main__":
    unittest.main()
