"""Conservative verification decision engine."""

from pathlib import Path

from contextguard.evidence import EvidenceReference
from contextguard.evidence_validator import validate_evidence_reference
from contextguard.schemas import FindingStatus, ReviewFinding
from contextguard.verification import VerificationResult


DEFAULT_CONFIDENCE_THRESHOLD = 0.75


def verify_finding(
    finding: ReviewFinding,
    confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
    evidence_references: list[EvidenceReference] | None = None,
    repository_root: str | Path | None = None,
) -> VerificationResult:
    """Keep findings only when confidence and supporting evidence meet the threshold."""

    if not 0.0 <= confidence_threshold <= 1.0:
        raise ValueError("Confidence threshold must be between 0.0 and 1.0")

    if not 0.0 <= finding.confidence <= 1.0:
        raise ValueError("Finding confidence must be between 0.0 and 1.0")

    references = list(evidence_references or [])
    validated_references = []

    if repository_root is not None:
        validated_references = [
            reference
            for reference in references
            if validate_evidence_reference(repository_root, reference)
        ]

    has_evidence = bool(finding.evidence or validated_references)

    if finding.confidence >= confidence_threshold and has_evidence:
        return VerificationResult(
            finding=finding,
            status=FindingStatus.KEEP,
            reason="Confidence threshold met and supporting evidence provided.",
            evidence=list(finding.evidence),
            evidence_references=validated_references,
        )

    if finding.confidence < confidence_threshold:
        reason = "Finding confidence is below the threshold."
    elif references and not validated_references and not finding.evidence:
        if repository_root is None:
            reason = "Structured evidence requires a repository root for validation."
        else:
            reason = "No structured evidence reference matched repository source."
    else:
        reason = "Insufficient confidence or supporting evidence."

    return VerificationResult(
        finding=finding,
        status=FindingStatus.UNCERTAIN,
        reason=reason,
        evidence=list(finding.evidence),
        evidence_references=validated_references,
    )
