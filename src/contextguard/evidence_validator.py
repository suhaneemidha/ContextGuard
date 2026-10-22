"""Validate evidence references against repository source files."""

from pathlib import Path

from contextguard.evidence import EvidenceReference


def validate_evidence_reference(
    repository_root: str | Path,
    reference: EvidenceReference,
) -> bool:
    """Return whether a reference matches the specified source lines."""
    root = Path(repository_root).resolve()
    candidate = (root / reference.file_path).resolve()

    # Prevent references from escaping the repository directory.
    if not candidate.is_relative_to(root):
        return False

    if not candidate.is_file():
        return False

    try:
        lines = candidate.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError):
        return False

    if reference.end_line > len(lines):
        return False

    actual_excerpt = "\n".join(
        lines[reference.start_line - 1 : reference.end_line]
    )

    return actual_excerpt.strip() == reference.excerpt.strip()
