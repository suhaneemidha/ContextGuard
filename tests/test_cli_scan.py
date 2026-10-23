import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from contextguard.cli import main


class TestScanCLI(unittest.TestCase):
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
                "findings": [
                    {
                        "title": "Potential data exposure",
                        "description": "The function returns user data.",
                        "file_path": "auth.py",
                        "line_number": 2,
                        "confidence": 0.95,
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
                ]
            }
        )

    def make_args(self, extra=None):
        return [
            "scan",
            "--repository", str(self.root),
            "--query", "return user_data",
            "--top-k", "1",
            "--window", "0",
            "--model", "test-model",
            *(extra or []),
        ]

    def run_scan(self, response, extra=None):
        stdout = io.StringIO()
        stderr = io.StringIO()

        with patch(
            "contextguard.cli.generate_scan_response",
            return_value=response,
        ) as provider:
            with contextlib.redirect_stdout(stdout):
                with contextlib.redirect_stderr(stderr):
                    exit_code = main(self.make_args(extra))

        return exit_code, stdout.getvalue(), stderr.getvalue(), provider

    def test_scan_accepts_matching_source_evidence(self):
        exit_code, output, _, provider = self.run_scan(self.make_response())

        result = json.loads(output)
        self.assertEqual(exit_code, 0)
        provider.assert_called_once()
        self.assertEqual(provider.call_args.kwargs["model"], "test-model")
        self.assertEqual(result["summary"]["findings_returned"], 1)
        self.assertEqual(result["summary"]["actionable_findings"], 1)
        self.assertTrue(result["findings"][0]["actionable"])
        self.assertEqual(
            result["findings"][0]["evidence_references"][0]["excerpt"],
            "    return user_data",
        )

    def test_scan_rejects_mismatched_evidence(self):
        exit_code, output, _, _ = self.run_scan(
            self.make_response("    return admin_data")
        )

        result = json.loads(output)
        self.assertEqual(exit_code, 0)
        self.assertEqual(result["summary"]["actionable_findings"], 0)
        self.assertFalse(result["findings"][0]["actionable"])
        self.assertEqual(result["findings"][0]["status"], "uncertain")
        self.assertEqual(result["findings"][0]["evidence_references"], [])

    def test_scan_accepts_empty_findings_list(self):
        exit_code, output, _, _ = self.run_scan('{"findings": []}')

        result = json.loads(output)
        self.assertEqual(exit_code, 0)
        self.assertEqual(result["summary"]["findings_returned"], 0)
        self.assertEqual(result["findings"], [])

    def test_scan_rejects_invalid_confidence_threshold(self):
        stdout = io.StringIO()
        stderr = io.StringIO()

        with patch("contextguard.cli.generate_scan_response") as provider:
            with contextlib.redirect_stdout(stdout):
                with contextlib.redirect_stderr(stderr):
                    exit_code = main(
                        self.make_args(["--confidence-threshold", "1.5"])
                    )

        self.assertEqual(exit_code, 2)
        self.assertIn("confidence-threshold", stderr.getvalue())
        provider.assert_not_called()


if __name__ == "__main__":
    unittest.main()
