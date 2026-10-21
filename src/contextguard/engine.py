"""Initial conservative verification decision engine."""

from contextguard.schemas import FindingStatus, ReviewFinding
from contextguard.verification import VerificationResult


DEFAULT_CONFIDENCE_THRESHOLD = 0.75


def verify_finding(
    finding: ReviewFinding,
    confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
) -> VerificationResult:
    """Keep findings only when confidence and evidence meet the threshold."""

    if not 0.0 <= confidence_threshold <= 1.0:
        raise ValueError("Confidence threshold must be between 0.0 and 1.0")

    if not 0.0 <= finding.confidence <= 1.0:
        raise ValueError("Finding confidence must be between 0.0 and 1.0")

    if finding.confidence >= confidence_threshold and finding.evidence:
        return VerificationResult(
            finding=finding,
            status=FindingStatus.KEEP,
            reason="Confidence threshold met and supporting evidence provided.",
            evidence=list(finding.evidence),
        )

    return VerificationResult(
        finding=finding,
        status=FindingStatus.UNCERTAIN,
        reason="Insufficient confidence or supporting evidence.",
        evidence=list(finding.evidence),
    )
