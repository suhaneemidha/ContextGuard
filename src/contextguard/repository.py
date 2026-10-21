"""Safe source-file ingestion for local repositories."""

from pathlib import Path

from contextguard.context import RepositoryFile


IGNORED_DIRS = {
    ".git",
    ".venv",
    "__pycache__",
    "node_modules",
    "dist",
    "build",
}

IGNORED_FILES = {
    ".env",
}

MAX_FILE_BYTES = 1_000_000


def load_repository(root: str | Path) -> list[RepositoryFile]:
    """Load readable, reasonably sized text files under a repository root."""
    root_path = Path(root).resolve()

    if not root_path.is_dir():
        raise NotADirectoryError(f"Repository root is not a directory: {root_path}")

    loaded: list[RepositoryFile] = []

    for path in sorted(root_path.rglob("*")):
        if not path.is_file():
            continue

        relative_path = path.relative_to(root_path)

        if any(part in IGNORED_DIRS for part in relative_path.parts):
            continue

        if path.name in IGNORED_FILES or path.name.endswith((".pyc", ".pyo")):
            continue

        try:
            if path.stat().st_size > MAX_FILE_BYTES:
                continue

            content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue

        loaded.append(
            RepositoryFile(
                path=relative_path.as_posix(),
                content=content,
            )
        )

    return loaded
