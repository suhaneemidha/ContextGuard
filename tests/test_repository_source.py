import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from contextguard.repository_source import (
    normalize_github_url,
    open_repository,
)


class TestGitHubURLNormalization(unittest.TestCase):
    def test_normalizes_public_repository_url(self):
        self.assertEqual(
            normalize_github_url("https://github.com/example/project"),
            "https://github.com/example/project.git",
        )

    def test_normalizes_url_with_git_suffix(self):
        self.assertEqual(
            normalize_github_url("https://github.com/example/project.git"),
            "https://github.com/example/project.git",
        )

    def test_accepts_trailing_slash(self):
        self.assertEqual(
            normalize_github_url("https://github.com/example/project/"),
            "https://github.com/example/project.git",
        )

    def test_rejects_non_github_hosts(self):
        with self.assertRaises(ValueError):
            normalize_github_url("https://example.com/example/project")

    def test_rejects_non_https_urls(self):
        with self.assertRaises(ValueError):
            normalize_github_url("http://github.com/example/project")

    def test_rejects_credentials_in_url(self):
        with self.assertRaises(ValueError):
            normalize_github_url(
                "https://user:password@github.com/example/project"
            )

    def test_rejects_extra_path_or_query(self):
        for url in (
            "https://github.com/example/project/tree/main",
            "https://github.com/example/project?tab=readme",
        ):
            with self.subTest(url=url):
                with self.assertRaises(ValueError):
                    normalize_github_url(url)

    def test_rejects_invalid_repository_path(self):
        for url in (
            "https://github.com/",
            "https://github.com/example",
            "https://github.com/example/..",
        ):
            with self.subTest(url=url):
                with self.assertRaises(ValueError):
                    normalize_github_url(url)


class TestOpenRepository(unittest.TestCase):
    def test_opens_existing_local_directory(self):
        with tempfile.TemporaryDirectory() as temporary:
            with open_repository(temporary) as root:
                self.assertEqual(root, Path(temporary).resolve())

    def test_rejects_empty_source(self):
        with self.assertRaises(ValueError):
            with open_repository(" "):
                pass

    def test_rejects_nonexistent_local_directory(self):
        with self.assertRaises(NotADirectoryError):
            with open_repository("/definitely/not/a/repository"):
                pass


if __name__ == "__main__":
    unittest.main()
