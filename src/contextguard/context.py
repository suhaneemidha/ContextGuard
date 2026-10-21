"""Data models for repository source code and retrieved context."""

from dataclasses import dataclass


@dataclass(frozen=True)
class RepositoryFile:
    """A source file collected from a repository."""

    path: str
    content: str


@dataclass(frozen=True)
class ContextSnippet:
    """A relevant section retrieved from a repository file."""

    file_path: str
    content: str
    start_line: int
    end_line: int
    relevance_score: float = 0.0
