import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from contextguard.repository import load_repository


class TestRepositoryIngestion(unittest.TestCase):
    def test_loads_text_files_with_relative_paths(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "app.py").write_text("print('hello')", encoding="utf-8")

            files = load_repository(root)

            self.assertEqual(len(files), 1)
            self.assertEqual(files[0].path, "app.py")
            self.assertEqual(files[0].content, "print('hello')")

    def test_skips_ignored_directories_and_env_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "app.py").write_text("print(1)", encoding="utf-8")
            (root / ".env").write_text("SECRET=value", encoding="utf-8")

            ignored = root / ".venv"
            ignored.mkdir()
            (ignored / "hidden.py").write_text("secret", encoding="utf-8")

            files = load_repository(root)
            paths = {file.path for file in files}

            self.assertEqual(paths, {"app.py"})

    def test_rejects_non_directory_root(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "file.txt"
            file_path.write_text("hello", encoding="utf-8")

            with self.assertRaises(NotADirectoryError):
                load_repository(file_path)


if __name__ == "__main__":
    unittest.main()
