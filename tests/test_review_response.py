import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from contextguard.evidence import EvidenceReference
from contextguard.review_response import (
    ParsedReviewResponse,
    parse_review_response,
)
from contextguard.schemas import FindingStatus


class TestReviewResponseParser(unittest.TestCase):
    def valid_payload(self):
        return {
            "status": "keep",
            "confidence": 0.91,
            "reason": "The supplied source supports the finding.",
            "evidence_references": [
                {
                    "file_path": "src/auth.py",
                    "start_line": 10,
                    "end_line": 11,
                    "excerpt": "if not authorized:\n    return None",
                    "explanation": "The source contains the relevant check.",
                }
            ],
        }

    def test_parses_valid_response(self):
        result = parse_review_response(json.dumps(self.valid_payload()))

        self.assertIsInstance(result, ParsedReviewResponse)
        self.assertEqual(result.status, FindingStatus.KEEP)
        self.assertEqual(result.confidence, 0.91)
        self.assertEqual(len(result.evidence_references), 1)
        self.assertIsInstance(result.evidence_references[0], EvidenceReference)
        self.assertEqual(result.evidence_references[0].file_path, "src/auth.py")

    def test_parses_uncertain_response_without_evidence(self):
        payload = self.valid_payload()
        payload["status"] = "uncertain"
        payload["confidence"] = 0.4
        payload["evidence_references"] = []

        result = parse_review_response(json.dumps(payload))

        self.assertEqual(result.status, FindingStatus.UNCERTAIN)
        self.assertEqual(result.evidence_references, ())

    def test_rejects_empty_or_invalid_json(self):
        for raw in ("", "not json", "[]", "null"):
            with self.subTest(raw=raw):
                with self.assertRaises(ValueError):
                    parse_review_response(raw)

    def test_rejects_invalid_status(self):
        payload = self.valid_payload()
        payload["status"] = "probably"

        with self.assertRaises(ValueError):
            parse_review_response(json.dumps(payload))

    def test_rejects_invalid_confidence(self):
        for confidence in (-0.1, 1.1, True, "0.9", None):
            with self.subTest(confidence=confidence):
                payload = self.valid_payload()
                payload["confidence"] = confidence
                with self.assertRaises(ValueError):
                    parse_review_response(json.dumps(payload))

    def test_rejects_missing_reason(self):
        payload = self.valid_payload()
        payload["reason"] = "   "

        with self.assertRaises(ValueError):
            parse_review_response(json.dumps(payload))

    def test_rejects_non_list_evidence_references(self):
        payload = self.valid_payload()
        payload["evidence_references"] = {}

        with self.assertRaises(ValueError):
            parse_review_response(json.dumps(payload))

    def test_rejects_invalid_evidence_reference(self):
        payload = self.valid_payload()
        payload["evidence_references"][0]["start_line"] = 0

        with self.assertRaises(ValueError):
            parse_review_response(json.dumps(payload))

    def test_rejects_non_integer_line_numbers(self):
        payload = self.valid_payload()
        payload["evidence_references"][0]["start_line"] = 10.5

        with self.assertRaises(ValueError):
            parse_review_response(json.dumps(payload))


if __name__ == "__main__":
    unittest.main()
