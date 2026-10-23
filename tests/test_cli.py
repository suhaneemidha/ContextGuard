import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from contextguard.cli import main


class TestContextGuardCLI(unittest.TestCase):
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

    def finding_args(self):
        return [
            "--title", "Potential data exposure",
            "--description", "The function may return user data.",
            "--file", "auth.py",
            "--line", "2",
            "--confidence", "0.8",
        ]

    def make_response(self, excerpt="    return user_data"):
        return {
            "status": "keep",
            "confidence": 0.95,
            "reason": "The source supports the finding.",
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

    def test_prepare_prints_review_prompt(self):
        output = io.StringIO()
        args = [
            "prepare",
            "--repository", str(self.root),
            "--query", "return user_data",
            "--window", "0",
            *self.finding_args(),
        ]

        with contextlib.redirect_stdout(output):
            exit_code = main(args)

        self.assertEqual(exit_code, 0)
        self.assertIn("Potential data exposure", output.getvalue())
        self.assertIn("return user_data", output.getvalue())

    def test_verify_prints_actionable_result_for_matching_evidence(self):
        response_path = self.root / "response.json"
        response_path.write_text(
            json.dumps(self.make_response()),
            encoding="utf-8",
        )
        output = io.StringIO()
        args = [
            "verify",
            "--repository", str(self.root),
            "--response-file", str(response_path),
            *self.finding_args(),
        ]

        with contextlib.redirect_stdout(output):
            exit_code = main(args)

        result = json.loads(output.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(result["status"], "keep")
        self.assertTrue(result["actionable"])
        self.assertEqual(len(result["evidence_references"]), 1)

    def test_verify_marks_mismatched_evidence_uncertain(self):
        response_path = self.root / "response.json"
        response_path.write_text(
            json.dumps(self.make_response("    return admin_data")),
            encoding="utf-8",
        )
        output = io.StringIO()
        args = [
            "verify",
            "--repository", str(self.root),
            "--response-file", str(response_path),
            *self.finding_args(),
        ]

        with contextlib.redirect_stdout(output):
            exit_code = main(args)

        result = json.loads(output.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(result["status"], "uncertain")
        self.assertFalse(result["actionable"])

    def test_invalid_confidence_returns_error_code(self):
        output = io.StringIO()
        errors = io.StringIO()
        args = [
            "prepare",
            "--repository", str(self.root),
            "--confidence", "1.5",
            "--title", "Possible bug",
            "--description", "Needs review.",
            "--file", "auth.py",
        ]

        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
            exit_code = main(args)

        self.assertEqual(exit_code, 2)
        self.assertIn("--confidence must be between", errors.getvalue())


if __name__ == "__main__":
    unittest.main()
