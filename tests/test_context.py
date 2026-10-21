import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from contextguard.context import ContextSnippet, RepositoryFile


class TestRepositoryContext(unittest.TestCase):
    def test_repository_file_stores_path_and_content(self):
        file = RepositoryFile(path="src/app.py", content="print(1)")

        self.assertEqual(file.path, "src/app.py")
        self.assertEqual(file.content, "print(1)")

    def test_context_snippet_stores_line_range_and_score(self):
        snippet = ContextSnippet(
            file_path="src/app.py",
            content="return result",
            start_line=4,
            end_line=4,
            relevance_score=0.95,
        )

        self.assertEqual(snippet.start_line, 4)
        self.assertEqual(snippet.end_line, 4)
        self.assertEqual(snippet.relevance_score, 0.95)

    def test_context_models_are_immutable(self):
        file = RepositoryFile(path="src/app.py", content="print(1)")

        with self.assertRaises(AttributeError):
            file.path = "other.py"


if __name__ == "__main__":
    unittest.main()
