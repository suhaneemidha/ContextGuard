import os
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from contextguard.llm import (
    DEFAULT_MODEL,
    generate_review_response,
    generate_scan_response,
)


class TestGroqReviewProvider(unittest.TestCase):
    def mock_response(self, content='{"status":"uncertain"}'):
        return SimpleNamespace(
            choices=[
                SimpleNamespace(message=SimpleNamespace(content=content))
            ]
        )

    def test_generates_json_response(self):
        with patch("contextguard.llm.load_dotenv"):
            with patch("contextguard.llm.Groq") as mock_groq:
                client = mock_groq.return_value
                client.chat.completions.create.return_value = self.mock_response()

                result = generate_review_response(
                    "Review this code.",
                    api_key="test-key",
                    model="test-model",
                )

        self.assertEqual(result, '{"status":"uncertain"}')
        mock_groq.assert_called_once_with(api_key="test-key")
        kwargs = client.chat.completions.create.call_args.kwargs
        self.assertEqual(kwargs["model"], "test-model")
        self.assertEqual(kwargs["response_format"]["type"], "json_schema")
        schema = kwargs["response_format"]["json_schema"]
        self.assertEqual(schema["name"], "contextguard_review_response")
        self.assertTrue(schema["strict"])
        self.assertIn("evidence_references", schema["schema"]["required"])

    def test_uses_default_model_when_not_configured(self):
        with patch("contextguard.llm.load_dotenv"):
            with patch("contextguard.llm.Groq") as mock_groq:
                mock_groq.return_value.chat.completions.create.return_value = (
                    self.mock_response()
                )
                generate_review_response("Review this code.", api_key="test-key")

        kwargs = mock_groq.return_value.chat.completions.create.call_args.kwargs
        self.assertEqual(kwargs["model"], DEFAULT_MODEL)

    def test_rejects_empty_prompt(self):
        with self.assertRaisesRegex(ValueError, "prompt must not be empty"):
            generate_review_response("  ", api_key="test-key")

    def test_rejects_missing_api_key(self):
        with (
            patch("contextguard.llm.load_dotenv"),
            patch.dict(os.environ, {"GROQ_API_KEY": ""}),
        ):
            with self.assertRaisesRegex(ValueError, "API key is missing"):
                generate_review_response("Review this code.")

    def test_rejects_empty_model_name(self):
        with patch("contextguard.llm.load_dotenv"):
            with patch.dict(os.environ, {"GROQ_MODEL": ""}, clear=False):
                with self.assertRaisesRegex(
                    ValueError, "model name must not be empty"
                ):
                    generate_review_response(
                        "Review this code.",
                        api_key="test-key",
                        model=" ",
                    )

    def test_rejects_empty_model_response(self):
        with patch("contextguard.llm.load_dotenv"):
            with patch("contextguard.llm.Groq") as mock_groq:
                mock_groq.return_value.chat.completions.create.return_value = (
                    self.mock_response("  ")
                )
                with self.assertRaisesRegex(
                    RuntimeError, "empty review response"
                ):
                    generate_review_response(
                        "Review this code.", api_key="test-key"
                    )

    def test_handles_provider_errors(self):
        with patch("contextguard.llm.load_dotenv"):
            with patch("contextguard.llm.Groq") as mock_groq:
                mock_groq.return_value.chat.completions.create.side_effect = (
                    OSError("network unavailable")
                )
                with self.assertRaisesRegex(
                    RuntimeError, "Groq review request failed"
                ):
                    generate_review_response(
                        "Review this code.", api_key="test-key"
                    )


class TestGroqScanProvider(unittest.TestCase):
    def test_generates_scan_response_with_findings_schema(self):
        response_text = '{"findings": []}'
        fake_response = SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content=response_text)
                )
            ]
        )

        with patch("contextguard.llm.load_dotenv"):
            with patch("contextguard.llm.Groq") as mock_groq:
                client = mock_groq.return_value
                client.chat.completions.create.return_value = fake_response

                result = generate_scan_response(
                    "Scan this repository.",
                    api_key="test-key",
                    model="test-model",
                )

        self.assertEqual(result, response_text)
        mock_groq.assert_called_once_with(api_key="test-key")
        kwargs = client.chat.completions.create.call_args.kwargs
        self.assertEqual(kwargs["model"], "test-model")

        response_format = kwargs["response_format"]
        self.assertEqual(response_format["type"], "json_schema")
        schema_wrapper = response_format["json_schema"]
        self.assertEqual(schema_wrapper["name"], "contextguard_scan_response")
        self.assertTrue(schema_wrapper["strict"])

        schema = schema_wrapper["schema"]
        self.assertEqual(schema["required"], ["findings"])
        finding_schema = schema["properties"]["findings"]["items"]
        self.assertIn("title", finding_schema["required"])
        self.assertIn("evidence_references", finding_schema["required"])

    def test_scan_rejects_empty_prompt(self):
        with self.assertRaisesRegex(ValueError, "prompt must not be empty"):
            generate_scan_response(" ", api_key="test-key")

    def test_scan_handles_provider_errors(self):
        with patch("contextguard.llm.load_dotenv"):
            with patch("contextguard.llm.Groq") as mock_groq:
                mock_groq.return_value.chat.completions.create.side_effect = (
                    OSError("network unavailable")
                )
                with self.assertRaisesRegex(
                    RuntimeError, "Groq scan request failed"
                ):
                    generate_scan_response(
                        "Scan this repository.", api_key="test-key"
                    )


if __name__ == "__main__":
    unittest.main()
