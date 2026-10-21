"""Local lexical retrieval of relevant repository snippets."""

import math
import re
from collections import Counter

from contextguard.context import ContextSnippet, RepositoryFile


TOKEN_PATTERN = re.compile(r"[a-zA-Z_][a-zA-Z0-9_]*")

STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for",
    "from", "in", "is", "it", "of", "on", "or", "that", "the",
    "this", "to", "was", "were", "with",
}


def tokenize(text: str) -> set[str]:
    """Extract lowercase words and identifiers, preserving term frequency."""
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
    """Rank source lines using local inverse-document-frequency weighting."""
    if top_k < 1:
        raise ValueError("top_k must be at least 1")

    query_tokens = tokenize(query)
    if not query_tokens:
        return []

    lines_by_file = [
        (file.path, file.content.splitlines())
        for file in files
    ]

    all_lines = [
        (path, index + 1, line)
        for path, lines in lines_by_file
        for index, line in enumerate(lines)
        if line.strip()
    ]

    if not all_lines:
        return []

    document_tokens = [set(tokenize(line)) for _, _, line in all_lines]
    document_frequency = Counter()
    for tokens in document_tokens:
        document_frequency.update(tokens)

    total_lines = len(all_lines)
    query_weights = {
        token: math.log((total_lines + 1) / (document_frequency[token] + 1)) + 1
        for token in set(query_tokens)
    }
    query_weight_total = sum(query_weights.values())

    snippets: list[ContextSnippet] = []

    for (path, line_number, line), tokens in zip(all_lines, document_tokens):
        line_counts = Counter(tokens)
        matched = set(query_weights) & set(line_counts)

        if not matched:
            continue

        score = sum(
            query_weights[token] * (1 + math.log(line_counts[token]))
            for token in matched
        ) / query_weight_total

        snippets.append(
            ContextSnippet(
                file_path=path,
                content=line,
                start_line=line_number,
                end_line=line_number,
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
