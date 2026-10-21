"""Assemble retrieved repository snippets into bounded review context."""

from dataclasses import dataclass

from contextguard.context import ContextSnippet


@dataclass(frozen=True)
class AssembledContext:
    """Context text plus the source references used to construct it."""

    text: str
    sources: tuple[str, ...]
    character_count: int


def assemble_context(
    snippets: list[ContextSnippet],
    max_characters: int = 8000,
) -> AssembledContext:
    """Combine unique snippets in rank order within a character budget."""
    if max_characters < 1:
        raise ValueError("max_characters must be at least 1")

    sections: list[str] = []
    sources: list[str] = []
    seen: set[tuple[str, int, int, str]] = set()
    used_characters = 0

    for snippet in snippets:
        key = (
            snippet.file_path,
            snippet.start_line,
            snippet.end_line,
            snippet.content,
        )
        if key in seen:
            continue
        seen.add(key)

        source = (
            f"{snippet.file_path}:"
            f"{snippet.start_line}-{snippet.end_line}"
        )
        section = f"[{source}]\n{snippet.content}"
        separator = "\n\n" if sections else ""
        addition = separator + section

        if used_characters + len(addition) > max_characters:
            continue

        sections.append(section)
        sources.append(source)
        used_characters += len(addition)

    text = "\n\n".join(sections)

    return AssembledContext(
        text=text,
        sources=tuple(sources),
        character_count=len(text),
    )
