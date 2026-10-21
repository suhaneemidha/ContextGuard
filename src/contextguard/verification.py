"""Models for recording code-review verification decisions."""

from dataclasses import dataclass, field

from contextguard.schemas import FindingStatus, ReviewFinding


@dataclass
class VerificationResult:
    """A review finding plus the evidence behind its decision."""

    finding: ReviewFinding
    status: FindingStatus
    reason: str
    evidence: list[str] = field(default_factory=list)

    def is_actionable(self) -> bool:
        """Return whether the finding should be presented as confirmed."""
        return self.status == FindingStatus.KEEP
