import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from contextguard.context import RepositoryFile
from contextguard.retrieval import retrieve_context, tokenize


class TestContextRetrieval(unittest.TestCase):
    def setUp(self):
        self.files = [
            RepositoryFile(
                path="app.py",
                content="def handle_null(value):\n    if value is None:\n        return None\n    return value",
            ),
            RepositoryFile(
                path="config.py",
                content="DEFAULT_CONFIDENCE_THRESHOLD = 0.75",
            ),
        ]

    def test_retrieves_matching_code(self):
        results = retrieve_context("handle null value", self.files, top_k=3)

        self.assertTrue(results)
        self.assertEqual(results[0].file_path, "app.py")
        self.assertEqual(results[0].start_line, 1)

    def test_results_have_valid_scores_and_line_numbers(self):
        results = retrieve_context("value", self.files)

        self.assertTrue(results)
        for result in results:
            self.assertGreater(result.relevance_score, 0)
            self.assertLessEqual(result.relevance_score, 1)
            self.assertGreaterEqual(result.start_line, 1)

    def test_empty_query_returns_no_results(self):
        self.assertEqual(retrieve_context("the and is", self.files), [])

    def test_invalid_top_k_raises_error(self):
        with self.assertRaises(ValueError):
            retrieve_context("value", self.files, top_k=0)

    def test_tokenization_is_case_insensitive(self):
        self.assertEqual(tokenize("Null VALUE"), {"null", "value"})


if __name__ == "__main__":
    unittest.main()


class TestContextExpansion(unittest.TestCase):
    def setUp(self):
        self.files = [
            RepositoryFile(
                path="app.py",
                content="def handle(value):\n    if value is None:\n        return None\n    return value",
            )
        ]
        self.snippet = retrieve_context("value", self.files, top_k=5)[1]

    def test_expands_context_around_matching_line(self):
        from contextguard.retrieval import expand_context

        expanded = expand_context(self.snippet, self.files, window=1)

        self.assertEqual(expanded.start_line, 1)
        self.assertEqual(expanded.end_line, 3)
        self.assertIn("return None", expanded.content)

    def test_expansion_respects_file_boundaries(self):
        from contextguard.retrieval import expand_context

        expanded = expand_context(self.snippet, self.files, window=10)

        self.assertEqual(expanded.start_line, 1)
        self.assertEqual(expanded.end_line, 4)

    def test_negative_window_raises_error(self):
        from contextguard.retrieval import expand_context

        with self.assertRaises(ValueError):
            expand_context(self.snippet, self.files, window=-1)


if __name__ == "__main__":
    unittest.main()
