"""Structured evidence references for code-review verification."""

from dataclasses import dataclass


@dataclass(frozen=True)
class EvidenceReference:
    """A traceable piece of evidence from repository source code."""

    file_path: str
    start_line: int
    end_line: int
    excerpt: str
    explanation: str

    def __post_init__(self) -> None:
        if not self.file_path.strip():
            raise ValueError("Evidence file path must not be empty")
        if self.start_line < 1:
            raise ValueError("Evidence start line must be at least 1")
        if self.end_line < self.start_line:
            raise ValueError("Evidence end line must not precede start line")
        if not self.excerpt.strip():
            raise ValueError("Evidence excerpt must not be empty")
        if not self.explanation.strip():
            raise ValueError("Evidence explanation must not be empty")
