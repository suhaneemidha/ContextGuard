import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from contextguard.scan_response import (
    ParsedScanResponse,
    parse_scan_response,
)


class TestScanResponseParser(unittest.TestCase):
    def valid_payload(self):
        return {
            "findings": [
                {
                    "title": "Potential data exposure",
                    "description": "The function returns user data.",
                    "file_path": "src/auth.py",
                    "line_number": 12,
                    "confidence": 0.91,
                    "evidence_references": [
                        {
                            "file_path": "src/auth.py",
                            "start_line": 12,
                            "end_line": 12,
                            "excerpt": "return user_data",
                            "explanation": "The function returns user data.",
                        }
                    ],
                }
            ]
        }

    def test_parses_valid_scan_response(self):
        result = parse_scan_response(json.dumps(self.valid_payload()))

        self.assertIsInstance(result, ParsedScanResponse)
        self.assertEqual(len(result.findings), 1)

        finding = result.findings[0]
        self.assertEqual(finding.title, "Potential data exposure")
        self.assertEqual(finding.file_path, "src/auth.py")
        self.assertEqual(finding.line_number, 12)
        self.assertEqual(finding.confidence, 0.91)
        self.assertEqual(len(finding.evidence_references), 1)
        self.assertEqual(
            finding.evidence_references[0].excerpt,
            "return user_data",
        )

    def test_accepts_empty_findings_list(self):
        result = parse_scan_response('{"findings": []}')

        self.assertEqual(result.findings, ())

    def test_rejects_empty_or_invalid_json(self):
        for raw in ("", "not json", "[]", "null"):
            with self.subTest(raw=raw):
                with self.assertRaises(ValueError):
                    parse_scan_response(raw)

    def test_rejects_missing_or_non_list_findings(self):
        for payload in ({}, {"findings": {}}, {"findings": None}):
            with self.subTest(payload=payload):
                with self.assertRaises(ValueError):
                    parse_scan_response(json.dumps(payload))

    def test_rejects_invalid_confidence(self):
        for confidence in (-0.1, 1.1, True, "0.9", None, float("nan")):
            with self.subTest(confidence=confidence):
                payload = self.valid_payload()
                payload["findings"][0]["confidence"] = confidence
                with self.assertRaises(ValueError):
                    parse_scan_response(json.dumps(payload))

    def test_rejects_invalid_line_number(self):
        for line_number in (0, -1, True, 2.5, "12"):
            with self.subTest(line_number=line_number):
                payload = self.valid_payload()
                payload["findings"][0]["line_number"] = line_number
                with self.assertRaises(ValueError):
                    parse_scan_response(json.dumps(payload))

    def test_rejects_missing_finding_fields(self):
        required_fields = (
            "title",
            "description",
            "file_path",
            "line_number",
            "confidence",
            "evidence_references",
        )

        for field in required_fields:
            with self.subTest(field=field):
                payload = self.valid_payload()
                del payload["findings"][0][field]
                with self.assertRaises(ValueError):
                    parse_scan_response(json.dumps(payload))

    def test_rejects_invalid_evidence_reference(self):
        payload = self.valid_payload()
        payload["findings"][0]["evidence_references"][0]["start_line"] = 0

        with self.assertRaises(ValueError):
            parse_scan_response(json.dumps(payload))

    def test_rejects_non_list_evidence_references(self):
        payload = self.valid_payload()
        payload["findings"][0]["evidence_references"] = {}

        with self.assertRaises(ValueError):
            parse_scan_response(json.dumps(payload))

    def test_rejects_non_object_finding(self):
        with self.assertRaises(ValueError):
            parse_scan_response('{"findings": ["not a finding"]}')


if __name__ == "__main__":
    unittest.main()
