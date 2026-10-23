"""End-to-end orchestration for repository-grounded code review."""

from dataclasses import dataclass, replace
from pathlib import Path

from contextguard.context_builder import AssembledContext
from contextguard.engine import DEFAULT_CONFIDENCE_THRESHOLD, verify_finding
from contextguard.review_context import build_review_context
from contextguard.review_prompt import build_review_prompt
from contextguard.review_response import parse_review_response
from contextguard.schemas import FindingStatus, ReviewFinding
from contextguard.verification import VerificationResult


@dataclass(frozen=True)
class ReviewRequest:
    """Prompt and repository context prepared for a review."""

    prompt: str
    context: AssembledContext


def prepare_review_request(
    repository_root: str | Path,
    finding: ReviewFinding,
    query: str | None = None,
    top_k: int = 5,
    window: int = 3,
    max_characters: int = 8000,
) -> ReviewRequest:
    """Retrieve repository context and build a prompt for a candidate finding."""
    retrieval_query = query or (
        f"{finding.title} {finding.description} {finding.file_path}"
    )

    context = build_review_context(
        repository_root=repository_root,
        query=retrieval_query,
        top_k=top_k,
        window=window,
        max_characters=max_characters,
    )

    return ReviewRequest(
        prompt=build_review_prompt(finding, context),
        context=context,
    )


def process_review_response(
    repository_root: str | Path,
    finding: ReviewFinding,
    raw_response: str,
    confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
) -> VerificationResult:
    """Parse a model response and validate its evidence before accepting a decision."""
    parsed = parse_review_response(raw_response)

    # Use the model's confidence, but do not let legacy free-text evidence
    # bypass validation of the response's structured source references.
    candidate = replace(
        finding,
        confidence=parsed.confidence,
        evidence=[],
    )

    evidence_check = verify_finding(
        finding=candidate,
        confidence_threshold=confidence_threshold,
        evidence_references=list(parsed.evidence_references),
        repository_root=repository_root,
    )

    if evidence_check.status != FindingStatus.KEEP:
        return VerificationResult(
            finding=candidate,
            status=FindingStatus.UNCERTAIN,
            reason=evidence_check.reason,
            evidence_references=evidence_check.evidence_references,
        )

    if parsed.status == FindingStatus.UNCERTAIN:
        return VerificationResult(
            finding=candidate,
            status=FindingStatus.UNCERTAIN,
            reason=parsed.reason,
            evidence_references=evidence_check.evidence_references,
        )

    # KEEP and FILTER are accepted only after confidence and source evidence
    # have passed the conservative verification gate.
    return VerificationResult(
        finding=candidate,
        status=parsed.status,
        reason=parsed.reason,
        evidence_references=evidence_check.evidence_references,
    )
