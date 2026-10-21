"""Local lexical retrieval of relevant repository snippets."""

import re

from contextguard.context import ContextSnippet, RepositoryFile


TOKEN_PATTERN = re.compile(r"[a-zA-Z_][a-zA-Z0-9_]*")

STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for",
    "from", "in", "is", "it", "of", "on", "or", "that", "the",
    "this", "to", "was", "were", "with",
}


def tokenize(text: str) -> set[str]:
    """Extract lowercase, meaningful identifier and word tokens."""
    return {
        token.lower()
        for token in TOKEN_PATTERN.findall(text)
        if token.lower() not in STOP_WORDS
    }


def retrieve_context(
    query: str,
    files: list[RepositoryFile],
    top_k: int = 5,
) -> list[ContextSnippet]:
    """Return the highest-overlap source snippets for a query."""
    if top_k < 1:
        raise ValueError("top_k must be at least 1")

    query_tokens = tokenize(query)
    if not query_tokens:
        return []

    snippets: list[ContextSnippet] = []

    for file in files:
        lines = file.content.splitlines()

        for index, line in enumerate(lines):
            line_tokens = tokenize(line)
            overlap = query_tokens & line_tokens

            if not overlap:
                continue

            score = len(overlap) / len(query_tokens)
            snippets.append(
                ContextSnippet(
                    file_path=file.path,
                    content=line,
                    start_line=index + 1,
                    end_line=index + 1,
                    relevance_score=score,
                )
            )

    snippets.sort(
        key=lambda snippet: (
            -snippet.relevance_score,
            snippet.file_path,
            snippet.start_line,
        )
    )

    return snippets[:top_k]


def expand_context(
    snippet: ContextSnippet,
    files: list[RepositoryFile],
    window: int = 3,
) -> ContextSnippet:
    """Expand a snippet with nearby lines from the same repository file."""
    if window < 0:
        raise ValueError("window must be non-negative")

    matching_file = next(
        (file for file in files if file.path == snippet.file_path),
        None,
    )
    if matching_file is None:
        raise ValueError(f"Repository file not found: {snippet.file_path}")

    lines = matching_file.content.splitlines()
    if not lines:
        raise ValueError("Cannot expand context from an empty file")

    start = max(1, snippet.start_line - window)
    end = min(len(lines), snippet.end_line + window)

    return ContextSnippet(
        file_path=snippet.file_path,
        content="\n".join(lines[start - 1:end]),
        start_line=start,
        end_line=end,
        relevance_score=snippet.relevance_score,
    )
