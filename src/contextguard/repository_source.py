"""Resolve local repository paths and public GitHub repository URLs."""

import re
import subprocess
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator
from urllib.parse import urlparse


GITHUB_PATH_PATTERN = re.compile(
    r"^/([A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?)/"
    r"([A-Za-z0-9._-]+)/?$"
)


def normalize_github_url(source: str) -> str:
    """Validate a standard HTTPS GitHub repository URL."""
    parsed = urlparse(source.strip())

    if (
        parsed.scheme != "https"
        or parsed.hostname != "github.com"
        or parsed.username is not None
        or parsed.password is not None
        or parsed.port is not None
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError(
            "Use a standard HTTPS GitHub repository URL, "
            "such as https://github.com/owner/repository"
        )

    match = GITHUB_PATH_PATTERN.fullmatch(parsed.path)
    if not match:
        raise ValueError(
            "GitHub URL must identify a repository as "
            "https://github.com/owner/repository"
        )

    owner, repository = match.groups()
    repository = repository.removesuffix(".git")

    if not repository or repository in {".", ".."}:
        raise ValueError("GitHub repository name is invalid")

    if repository.startswith(".") or repository.endswith("."):
        raise ValueError("GitHub repository name is invalid")

    return f"https://github.com/{owner}/{repository}.git"


@contextmanager
def open_repository(source: str | Path) -> Iterator[Path]:
    """Yield a local repository path, cloning HTTPS GitHub URLs temporarily."""
    value = str(source).strip()

    if not value:
        raise ValueError("Repository path or URL must not be empty")

    if value.startswith(("https://", "http://")):
        clone_url = normalize_github_url(value)

        with tempfile.TemporaryDirectory(prefix="contextguard-") as temporary:
            destination = Path(temporary) / "repository"

            try:
                subprocess.run(
                    [
                        "git",
                        "clone",
                        "--depth",
                        "1",
                        "--",
                        clone_url,
                        str(destination),
                    ],
                    check=True,
                    capture_output=True,
                    text=True,
                    timeout=120,
                )
            except FileNotFoundError as exc:
                raise RuntimeError(
                    "Git is required to clone a GitHub repository."
                ) from exc
            except subprocess.TimeoutExpired as exc:
                raise RuntimeError(
                    "GitHub clone timed out after 120 seconds."
                ) from exc
            except subprocess.CalledProcessError as exc:
                details = (exc.stderr or "").strip()
                raise RuntimeError(
                    "Could not clone the GitHub repository."
                    + (f" Details: {details}" if details else "")
                ) from exc

            yield destination
        return

    root = Path(value).expanduser().resolve()
    if not root.is_dir():
        raise NotADirectoryError(
            f"Repository path is not a directory: {root}"
        )

    yield root
