import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from contextguard.review_context import build_review_context


class TestReviewContextPipeline(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

        (self.root / "auth.py").write_text(
            "def auth():\n"
            "    check_access()\n"
            "    audit_event()\n"
            "    return data\n",
            encoding="utf-8",
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_builds_context_from_relevant_repository_code(self):
        result = build_review_context(
            repository_root=self.root,
            query="check_access",
            top_k=1,
            window=1,
        )

        self.assertIn("auth.py:", result.text)
        self.assertIn("check_access()", result.text)
        self.assertIn("audit_event()", result.text)
        self.assertGreater(result.character_count, 0)
        self.assertIn("auth.py:1-3", result.sources)

    def test_respects_character_budget(self):
        result = build_review_context(
            repository_root=self.root,
            query="check_access",
            top_k=1,
            window=1,
            max_characters=20,
        )

        self.assertLessEqual(result.character_count, 20)

    def test_empty_query_returns_empty_context(self):
        result = build_review_context(
            repository_root=self.root,
            query="",
        )

        self.assertEqual(result.text, "")
        self.assertEqual(result.sources, ())
        self.assertEqual(result.character_count, 0)

    def test_invalid_character_budget_raises_error(self):
        with self.assertRaises(ValueError):
            build_review_context(
                repository_root=self.root,
                query="check_access",
                max_characters=0,
            )


if __name__ == "__main__":
    unittest.main()
