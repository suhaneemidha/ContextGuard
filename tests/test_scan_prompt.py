import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from contextguard.context_builder import AssembledContext
from contextguard.scan_prompt import build_scan_prompt


class TestScanPrompt(unittest.TestCase):
    def setUp(self):
        self.context = AssembledContext(
            text=(
                "[src/auth.py:1-3]\n"
                "def get_user():\n"
                "    return user_data"
            ),
            sources=("src/auth.py:1-3",),
            character_count=55,
        )

    def test_includes_repository_source_context(self):
        prompt = build_scan_prompt(self.context)

        self.assertIn("src/auth.py:1-3", prompt)
        self.assertIn("def get_user():", prompt)
        self.assertIn("return user_data", prompt)

    def test_requires_exact_source_citations(self):
        prompt = build_scan_prompt(self.context)

        self.assertIn("Copy evidence excerpts verbatim", prompt)
        self.assertIn("exact line range", prompt)
        self.assertIn("line range must match the excerpt's boundaries", prompt)

    def test_requires_conservative_bug_discovery(self):
        prompt = build_scan_prompt(self.context)

        self.assertIn("Do not invent bugs", prompt)
        self.assertIn("untrusted data", prompt)
        self.assertIn("Avoid duplicate reports", prompt)

    def test_allows_no_findings_when_no_defect_is_supported(self):
        prompt = build_scan_prompt(self.context)

        self.assertIn("return an empty findings", prompt)
        self.assertIn("Confidence must be between 0.0 and 1.0", prompt)


if __name__ == "__main__":
    unittest.main()
