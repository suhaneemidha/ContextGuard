"""Pipeline for preparing repository context for code review."""

from pathlib import Path

from contextguard.context_builder import AssembledContext, assemble_context
from contextguard.repository import load_repository
from contextguard.retrieval import expand_context, retrieve_context


def build_review_context(
    repository_root: str | Path,
    query: str,
    top_k: int = 5,
    window: int = 3,
    max_characters: int = 8000,
) -> AssembledContext:
    """Retrieve relevant repository code and assemble bounded review context."""
    files = load_repository(repository_root)

    snippets = retrieve_context(
        query=query,
        files=files,
        top_k=top_k,
    )

    expanded_snippets = [
        expand_context(snippet, files, window=window)
        for snippet in snippets
    ]

    return assemble_context(
        expanded_snippets,
        max_characters=max_characters,
    )
