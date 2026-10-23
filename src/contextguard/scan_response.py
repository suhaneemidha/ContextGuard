"""Parse and validate automatic repository scan responses."""

import json
import math
from dataclasses import dataclass
from typing import Any

from contextguard.evidence import EvidenceReference


@dataclass(frozen=True)
class ParsedScanFinding:
    """A structurally validated potential bug from an automatic scan."""

    title: str
    description: str
    file_path: str
    line_number: int
    confidence: float
    evidence_references: tuple[EvidenceReference, ...]


@dataclass(frozen=True)
class ParsedScanResponse:
    """Validated findings returned by an automatic scan."""

    findings: tuple[ParsedScanFinding, ...]


def _require_string(value: Any, field_name: str) -> str:
    """Require a non-empty string."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"'{field_name}' must be a non-empty string")
    return value


def _parse_evidence_reference(
    item: Any,
    index: int,
    finding_index: int,
) -> EvidenceReference:
    """Validate one structured evidence reference."""
    if not isinstance(item, dict):
        raise ValueError(
            f"Evidence reference {index} for finding {finding_index} "
            "must be a JSON object"
        )

    start_line = item.get("start_line")
    end_line = item.get("end_line")

    if (
        isinstance(start_line, bool)
        or not isinstance(start_line, int)
        or isinstance(end_line, bool)
        or not isinstance(end_line, int)
    ):
        raise ValueError(
            f"Evidence line numbers for finding {finding_index} "
            "must be integers"
        )

    try:
        return EvidenceReference(
            file_path=_require_string(item.get("file_path"), "file_path"),
            start_line=start_line,
            end_line=end_line,
            excerpt=_require_string(item.get("excerpt"), "excerpt"),
            explanation=_require_string(item.get("explanation"), "explanation"),
        )
    except ValueError as exc:
        raise ValueError(
            f"Invalid evidence reference {index} for finding "
            f"{finding_index}: {exc}"
        ) from exc


def parse_scan_response(raw_response: str) -> ParsedScanResponse:
    """Parse scan JSON and validate findings and their evidence structures."""
    if not isinstance(raw_response, str) or not raw_response.strip():
        raise ValueError("Scan response must be a non-empty string")

    try:
        payload = json.loads(raw_response)
    except json.JSONDecodeError as exc:
        raise ValueError("Scan response must contain valid JSON") from exc

    if not isinstance(payload, dict):
        raise ValueError("Scan response must be a JSON object")

    raw_findings = payload.get("findings")
    if not isinstance(raw_findings, list):
        raise ValueError("'findings' must be a list")

    findings: list[ParsedScanFinding] = []

    for index, item in enumerate(raw_findings):
        if not isinstance(item, dict):
            raise ValueError(f"Finding {index} must be a JSON object")

        line_number = item.get("line_number")
        if (
            isinstance(line_number, bool)
            or not isinstance(line_number, int)
            or line_number < 1
        ):
            raise ValueError(
                f"Line number for finding {index} must be an integer at least 1"
            )

        confidence = item.get("confidence")
        if (
            isinstance(confidence, bool)
            or not isinstance(confidence, (int, float))
            or not math.isfinite(confidence)
            or not 0.0 <= confidence <= 1.0
        ):
            raise ValueError(
                f"Confidence for finding {index} must be a finite number "
                "between 0.0 and 1.0"
            )

        raw_references = item.get("evidence_references")
        if not isinstance(raw_references, list):
            raise ValueError(
                f"Evidence references for finding {index} must be a list"
            )

        references = tuple(
            _parse_evidence_reference(reference, ref_index, index)
            for ref_index, reference in enumerate(raw_references)
        )

        findings.append(
            ParsedScanFinding(
                title=_require_string(item.get("title"), "title"),
                description=_require_string(
                    item.get("description"), "description"
                ),
                file_path=_require_string(item.get("file_path"), "file_path"),
                line_number=line_number,
                confidence=float(confidence),
                evidence_references=references,
            )
        )

    return ParsedScanResponse(findings=tuple(findings))
