"""Parse and validate structured code-review model responses."""

import json
from dataclasses import dataclass
from typing import Any

from contextguard.evidence import EvidenceReference
from contextguard.schemas import FindingStatus


@dataclass(frozen=True)
class ParsedReviewResponse:
    """A validated response from the code-review model."""

    status: FindingStatus
    confidence: float
    reason: str
    evidence_references: tuple[EvidenceReference, ...]


def _require_string(value: Any, field_name: str) -> str:
    """Require a non-empty string field."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"'{field_name}' must be a non-empty string")
    return value


def parse_review_response(raw_response: str) -> ParsedReviewResponse:
    """Parse JSON and validate its decision, confidence, and evidence."""
    if not isinstance(raw_response, str) or not raw_response.strip():
        raise ValueError("Review response must be a non-empty string")

    try:
        payload = json.loads(raw_response)
    except json.JSONDecodeError as exc:
        raise ValueError("Review response must contain valid JSON") from exc

    if not isinstance(payload, dict):
        raise ValueError("Review response must be a JSON object")

    try:
        status = FindingStatus(_require_string(payload.get("status"), "status"))
    except ValueError as exc:
        raise ValueError("Status must be 'keep', 'filter', or 'uncertain'") from exc

    confidence = payload.get("confidence")
    if (
        isinstance(confidence, bool)
        or not isinstance(confidence, (int, float))
        or not 0.0 <= confidence <= 1.0
    ):
        raise ValueError("Confidence must be a number between 0.0 and 1.0")

    reason = _require_string(payload.get("reason"), "reason")
    raw_references = payload.get("evidence_references")

    if not isinstance(raw_references, list):
        raise ValueError("'evidence_references' must be a list")

    references: list[EvidenceReference] = []

    for index, item in enumerate(raw_references):
        if not isinstance(item, dict):
            raise ValueError(f"Evidence reference {index} must be a JSON object")

        start_line = item.get("start_line")
        end_line = item.get("end_line")

        if (
            isinstance(start_line, bool)
            or not isinstance(start_line, int)
            or isinstance(end_line, bool)
            or not isinstance(end_line, int)
        ):
            raise ValueError(
                f"Evidence reference {index} line numbers must be integers"
            )

        try:
            reference = EvidenceReference(
                file_path=_require_string(item.get("file_path"), "file_path"),
                start_line=start_line,
                end_line=end_line,
                excerpt=_require_string(item.get("excerpt"), "excerpt"),
                explanation=_require_string(
                    item.get("explanation"), "explanation"
                ),
            )
        except ValueError as exc:
            raise ValueError(
                f"Invalid evidence reference at index {index}: {exc}"
            ) from exc

        references.append(reference)

    return ParsedReviewResponse(
        status=status,
        confidence=float(confidence),
        reason=reason,
        evidence_references=tuple(references),
    )
