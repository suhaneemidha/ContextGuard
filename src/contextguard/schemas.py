"""Data schemas used throughout ContextGuard."""

from dataclasses import dataclass, field
from enum import Enum


class FindingStatus(str, Enum):
    """Possible verification outcomes for a review finding."""

    KEEP = "keep"
    FILTER = "filter"
    UNCERTAIN = "uncertain"


@dataclass
class ReviewFinding:
    """A potential issue identified during code review."""

    title: str
    description: str
    file_path: str
    line_number: int | None = None
    confidence: float = 0.0
    status: FindingStatus = FindingStatus.UNCERTAIN
    evidence: list[str] = field(default_factory=list)
