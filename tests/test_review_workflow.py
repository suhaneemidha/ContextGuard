import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from contextguard.review_workflow import (
    prepare_review_request,
    process_review_response,
)
from contextguard.schemas import FindingStatus, ReviewFinding


class TestReviewWorkflow(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        (self.root / "auth.py").write_text(
            "def get_user():\n"
            "    return user_data\n",
            encoding="utf-8",
        )
        self.finding = ReviewFinding(
            title="Potential data exposure",
            description="The function may return user data without authorization.",
            file_path="auth.py",
            line_number=2,
            confidence=0.9,
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def make_response(
        self,
        status="keep",
        confidence=0.95,
        excerpt="    return user_data",
    ):
        return json.dumps(
            {
                "status": status,
                "confidence": confidence,
                "reason": "The source evidence supports this decision.",
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

    def test_prepares_prompt_with_relevant_repository_context(self):
        request = prepare_review_request(
            repository_root=self.root,
            finding=self.finding,
            query="return user_data",
            top_k=1,
            window=0,
        )

        self.assertIn("Potential data exposure", request.prompt)
        self.assertIn("return user_data", request.prompt)
        self.assertGreater(request.context.character_count, 0)

    def test_accepts_matching_source_evidence(self):
        result = process_review_response(
            repository_root=self.root,
            finding=self.finding,
            raw_response=self.make_response(),
        )

        self.assertEqual(result.status, FindingStatus.KEEP)
        self.assertEqual(len(result.evidence_references), 1)
        self.assertTrue(result.is_actionable())

    def test_rejects_mismatched_source_evidence(self):
        result = process_review_response(
            repository_root=self.root,
            finding=self.finding,
            raw_response=self.make_response(excerpt="return admin_data"),
        )

        self.assertEqual(result.status, FindingStatus.UNCERTAIN)
        self.assertEqual(result.evidence_references, [])
        self.assertFalse(result.is_actionable())

    def test_low_confidence_remains_uncertain(self):
        result = process_review_response(
            repository_root=self.root,
            finding=self.finding,
            raw_response=self.make_response(confidence=0.4),
        )

        self.assertEqual(result.status, FindingStatus.UNCERTAIN)
        self.assertFalse(result.is_actionable())

    def test_model_uncertainty_is_preserved(self):
        result = process_review_response(
            repository_root=self.root,
            finding=self.finding,
            raw_response=self.make_response(status="uncertain"),
        )

        self.assertEqual(result.status, FindingStatus.UNCERTAIN)
        self.assertFalse(result.is_actionable())

    def test_filter_decision_requires_matching_evidence(self):
        result = process_review_response(
            repository_root=self.root,
            finding=self.finding,
            raw_response=self.make_response(
                status="filter",
                excerpt="    return user_data",
            ),
        )

        self.assertEqual(result.status, FindingStatus.FILTER)
        self.assertFalse(result.is_actionable())


if __name__ == "__main__":
    unittest.main()
