import unittest

from contextguard.context import ContextSnippet
from contextguard.context_builder import assemble_context


class TestContextBuilder(unittest.TestCase):
    def setUp(self):
        self.snippets = [
            ContextSnippet(
                file_path="src/app.py",
                content="def validate(value):",
                start_line=10,
                end_line=10,
                relevance_score=0.9,
            ),
            ContextSnippet(
                file_path="src/db.py",
                content="return connection",
                start_line=25,
                end_line=25,
                relevance_score=0.8,
            ),
        ]

    def test_assembles_context_with_source_references(self):
        result = assemble_context(self.snippets)
        self.assertIn("[src/app.py:10-10]", result.text)
        self.assertIn("[src/db.py:25-25]", result.text)
        self.assertEqual(len(result.sources), 2)
        self.assertEqual(result.character_count, len(result.text))

    def test_removes_duplicate_snippets(self):
        result = assemble_context([self.snippets[0], self.snippets[0]])
        self.assertEqual(len(result.sources), 1)
        self.assertEqual(result.text.count("def validate(value):"), 1)

    def test_respects_character_budget(self):
        result = assemble_context(self.snippets, max_characters=45)
        self.assertLessEqual(result.character_count, 45)
        self.assertEqual(len(result.sources), 1)

    def test_invalid_character_budget_raises_error(self):
        with self.assertRaises(ValueError):
            assemble_context(self.snippets, max_characters=0)


if __name__ == "__main__":
    unittest.main()
