import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from contextguard.cli import main


class TestReviewCLI(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        (self.root / "auth.py").write_text(
            "def get_user():\n"
            "    return user_data\n",
            encoding="utf-8",
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def make_response(self, excerpt="    return user_data"):
        return json.dumps(
            {
                "status": "keep",
                "confidence": 0.95,
                "reason": "The cited source supports the finding.",
                "evidence_references": [
                    {
                        "file_path": "auth.py",
                        "start_line": 2,
                        "end_line": 2,
                        "excerpt": excerpt,
                        "explanation": "This line returns user data.",
                    }
                ],
            }
        )

    def make_args(self, model="test-model"):
        return [
            "review",
            "--repository", str(self.root),
            "--title", "Potential data exposure",
            "--description", "The function may return user data.",
            "--file", "auth.py",
            "--line", "2",
            "--confidence", "0.8",
            "--query", "return user_data",
            "--window", "0",
            "--model", model,
        ]

    def test_review_uses_provider_and_accepts_matching_evidence(self):
        with patch(
            "contextguard.cli.generate_review_response",
            return_value=self.make_response(),
        ) as mocked_provider:
            with patch("builtins.print") as mocked_print:
                exit_code = main(self.make_args())

        self.assertEqual(exit_code, 0)
        mocked_provider.assert_called_once()
        self.assertEqual(
            mocked_provider.call_args.kwargs["model"],
            "test-model",
        )

        output = json.loads(mocked_print.call_args.args[0])
        self.assertEqual(output["status"], "keep")
        self.assertTrue(output["actionable"])
        self.assertEqual(len(output["evidence_references"]), 1)

    def test_review_rejects_mismatched_evidence(self):
        with patch(
            "contextguard.cli.generate_review_response",
            return_value=self.make_response("    return admin_data"),
        ):
            with patch("builtins.print") as mocked_print:
                exit_code = main(self.make_args())

        self.assertEqual(exit_code, 0)
        output = json.loads(mocked_print.call_args.args[0])
        self.assertEqual(output["status"], "uncertain")
        self.assertFalse(output["actionable"])
        self.assertEqual(output["evidence_references"], [])

    def test_review_reports_missing_api_key_without_calling_provider(self):
        with patch(
            "contextguard.cli.generate_review_response",
            side_effect=ValueError(
                "Groq API key is missing. Set GROQ_API_KEY in your .env file."
            ),
        ) as mocked_provider:
            with patch("sys.stderr") as mocked_stderr:
                exit_code = main(self.make_args())

        self.assertEqual(exit_code, 2)
        mocked_provider.assert_called_once()
        mocked_stderr.write.assert_called()


if __name__ == "__main__":
    unittest.main()
