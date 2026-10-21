import unittest

from contextguard.evidence import EvidenceReference


class TestEvidenceReference(unittest.TestCase):
    def test_creates_valid_evidence_reference(self):
        evidence = EvidenceReference(
            file_path="src/auth.py",
            start_line=10,
            end_line=12,
            excerpt="if not user.is_admin:",
            explanation="This condition restricts access to administrators.",
        )

        self.assertEqual(evidence.file_path, "src/auth.py")
        self.assertEqual(evidence.start_line, 10)
        self.assertEqual(evidence.end_line, 12)

    def test_rejects_empty_file_path(self):
        with self.assertRaises(ValueError):
            EvidenceReference("", 1, 1, "some code", "some explanation")

    def test_rejects_invalid_line_range(self):
        with self.assertRaises(ValueError):
            EvidenceReference("src/app.py", 5, 4, "some code", "explanation")

    def test_rejects_line_number_below_one(self):
        with self.assertRaises(ValueError):
            EvidenceReference("src/app.py", 0, 1, "some code", "explanation")

    def test_rejects_empty_excerpt_or_explanation(self):
        with self.assertRaises(ValueError):
            EvidenceReference("src/app.py", 1, 1, "", "explanation")

        with self.assertRaises(ValueError):
            EvidenceReference("src/app.py", 1, 1, "some code", "")

    def test_evidence_reference_is_immutable(self):
        evidence = EvidenceReference(
            "src/app.py", 1, 1, "return None", "Handles missing input."
        )

        with self.assertRaises(AttributeError):
            evidence.start_line = 2


if __name__ == "__main__":
    unittest.main()
