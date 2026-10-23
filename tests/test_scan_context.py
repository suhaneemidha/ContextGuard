import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from contextguard.scan_context import _is_test_file, build_scan_context


class TestScanContext(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        (self.root / "src" / "contextguard").mkdir(parents=True)
        (self.root / "tests").mkdir()

        (self.root / "src" / "contextguard" / "auth.py").write_text(
            "def get_user():\n"
            "    user = load_user()\n"
            "    return user\n",
            encoding="utf-8",
        )
        (self.root / "src" / "contextguard" / "storage.py").write_text(
            "def read_record(record_id):\n"
            "    path = DATA_DIR / record_id\n"
            "    return path.read_text()\n",
            encoding="utf-8",
        )
        (self.root / "tests" / "test_auth.py").write_text(
            "def test_security_validation_error():\n"
            "    assert True\n",
            encoding="utf-8",
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_scan_context_excludes_test_directories(self):
        result = build_scan_context(
            self.root,
            query="security validation error load_user record_id read_text",
            top_k=10,
            window=1,
        )
        self.assertNotIn("tests/test_auth.py", result.text)
        self.assertIn("src/contextguard/auth.py:", result.text)
        self.assertIn("src/contextguard/storage.py:", result.text)

    def test_scan_context_selects_at_most_one_seed_per_file(self):
        result = build_scan_context(
            self.root,
            query="user record path security validation",
            top_k=10,
            window=0,
        )
        source_paths = [source.split(":")[0] for source in result.sources]
        self.assertEqual(len(source_paths), len(set(source_paths)))

    def test_test_file_detection(self):
        self.assertTrue(_is_test_file("tests/test_auth.py"))
        self.assertTrue(_is_test_file("src/auth_test.py"))
        self.assertFalse(_is_test_file("src/auth.py"))

    def test_scan_context_covers_files_without_query_matches(self):
        result = build_scan_context(
            self.root,
            query="totally unrelated sentinel words",
            top_k=10,
            window=1,
        )
        self.assertIn("src/contextguard/auth.py:", result.text)
        self.assertIn("src/contextguard/storage.py:", result.text)
        self.assertNotIn("tests/test_auth.py", result.text)

    def test_scan_context_includes_complete_enclosing_function(self):
        result = build_scan_context(
            self.root,
            query="load_user",
            top_k=1,
            window=0,
        )
        self.assertIn("def get_user():", result.text)
        self.assertIn("user = load_user()", result.text)
        self.assertIn("return user", result.text)

    def test_safe_path_resolution_does_not_hide_validation_logic(self):
        (self.root / "safe_paths.py").write_text(
            "from pathlib import Path\n"
            "DATA_DIR = Path('/tmp/data').resolve()\n"
            "def read_user_file(filename: str) -> str:\n"
            "    path = (DATA_DIR / filename).resolve()\n"
            "    if not path.is_relative_to(DATA_DIR):\n"
            "        raise ValueError('path escapes data directory')\n"
            "    return path.read_text()\n",
            encoding="utf-8",
        )

        result = build_scan_context(
            self.root,
            query="resolve path validation",
            top_k=10,
            window=0,
        )

        safe_context = next(
            section for section in result.text.split("\n\n")
            if section.startswith("[safe_paths.py:")
        )
        self.assertIn("path.is_relative_to(DATA_DIR)", safe_context)
        self.assertIn("from pathlib import Path", safe_context)
        self.assertIn("path.read_text()", safe_context)

    def test_scan_context_includes_module_level_constants(self):
        (self.root / "query_engine.py").write_text(
            "ROW_CAP = 5000\n"
            "def execute_sql(query):\n"
            "    df = run_query(query)\n"
            "    truncated = False\n"
            "    if ROW_CAP is not None and len(df) > ROW_CAP:\n"
            "        truncated = True\n"
            "        df = df.head(ROW_CAP)\n"
            "    return df, truncated\n",
            encoding="utf-8",
        )

        result = build_scan_context(
            self.root,
            query="execute_sql ROW_CAP result rows",
            top_k=1,
            window=0,
        )

        self.assertIn("ROW_CAP = 5000", result.text)
        self.assertIn("def execute_sql(query):", result.text)

    def test_empty_query_returns_empty_context(self):
        result = build_scan_context(self.root, query="")
        self.assertEqual(result.text, "")
        self.assertEqual(result.sources, ())


if __name__ == "__main__":
    unittest.main()
