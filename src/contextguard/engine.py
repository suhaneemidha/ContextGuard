"""Conservative verification decision engine."""

from contextguard.evidence import EvidenceReference
from contextguard.schemas import FindingStatus, ReviewFinding
from contextguard.verification import VerificationResult


DEFAULT_CONFIDENCE_THRESHOLD = 0.75


def verify_finding(
    finding: ReviewFinding,
    confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
    evidence_references: list[EvidenceReference] | None = None,
) -> VerificationResult:
    """Keep findings only when confidence and supporting evidence meet the threshold."""

    if not 0.0 <= confidence_threshold <= 1.0:
        raise ValueError("Confidence threshold must be between 0.0 and 1.0")

    if not 0.0 <= finding.confidence <= 1.0:
        raise ValueError("Finding confidence must be between 0.0 and 1.0")

    references = list(evidence_references or [])
    has_evidence = bool(finding.evidence or references)

    if finding.confidence >= confidence_threshold and has_evidence:
        return VerificationResult(
            finding=finding,
            status=FindingStatus.KEEP,
            reason="Confidence threshold met and supporting evidence provided.",
            evidence=list(finding.evidence),
            evidence_references=references,
        )

    return VerificationResult(
        finding=finding,
        status=FindingStatus.UNCERTAIN,
        reason="Insufficient confidence or supporting evidence.",
        evidence=list(finding.evidence),
        evidence_references=references,
    )
