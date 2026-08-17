"""Tests for the project scaffolder (generated projects written to disk)."""

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from execution.project_scaffolder import ProjectScaffolder  # noqa: E402


class TestProjectScaffolder(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.sf = ProjectScaffolder(base_dir=self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_scaffold_writes_files(self):
        manifest = self.sf.scaffold("demo", {
            "README.md": "# demo",
            "src/app.py": "print('hi')\n",
        })
        self.assertTrue(manifest["ok"])
        self.assertEqual(manifest["file_count"], 2)
        app = Path(self.tmp.name) / "demo" / "src" / "app.py"
        self.assertTrue(app.exists())
        self.assertEqual(app.read_text(encoding="utf-8"), "print('hi')\n")

    def test_scaffold_normalizes_project_name(self):
        manifest = self.sf.scaffold("My App!/v2", {"app.py": "x"})
        self.assertEqual(manifest["project"], "My_App_v2")

    def test_path_traversal_blocked(self):
        manifest = self.sf.scaffold("safe", {"../evil.txt": "pwn", "ok.txt": "fine"})
        self.assertFalse(manifest["ok"])
        self.assertNotIn("../evil.txt", manifest["files"])
        self.assertEqual(len(manifest["errors"]), 1)
        self.assertFalse((Path(self.tmp.name).parent / "evil.txt").exists())
        self.assertTrue((Path(self.tmp.name) / "safe" / "ok.txt").exists())

    def test_absolute_path_stays_in_root(self):
        manifest = self.sf.scaffold("safe2", {"/etc/passwd": "x"})
        self.assertTrue(manifest["ok"])
        written = Path(self.tmp.name) / "safe2" / "etc" / "passwd"
        self.assertTrue(written.exists())

    def test_extract_json_block(self):
        text = 'Here is the project:\n{"files": {"a.py": "print(1)"}}\nThat is all.'
        self.assertEqual(ProjectScaffolder.extract_json_block(text)["files"]["a.py"],
                         "print(1)")
        self.assertEqual(ProjectScaffolder.extract_json_block("no json here"), {})

    def test_scaffold_from_json(self):
        manifest = self.sf.scaffold_from_json(
            '{"files": {"main.py": "print(2)"}}', "jsonproj"
        )
        self.assertTrue(manifest["ok"])
        self.assertTrue((Path(self.tmp.name) / "jsonproj" / "main.py").exists())

    def test_scaffold_from_flat_map(self):
        manifest = self.sf.scaffold_from_json(
            '{"app.py": "print(3)"}', "flatproj"
        )
        self.assertTrue(manifest["ok"])

    def test_scaffold_from_invalid_json(self):
        manifest = self.sf.scaffold_from_json("I have no idea what to write", "bad")
        self.assertFalse(manifest["ok"])

    def test_default_project(self):
        files = ProjectScaffolder.default_project("a todo api", "todo")
        self.assertIn("app.py", files)
        self.assertIn("README.md", files)
        self.assertIn("def main", files["app.py"])

    def test_list_and_remove(self):
        self.sf.scaffold("l1", {"a.txt": "1"})
        self.sf.scaffold("l2", {"b.txt": "2"})
        listing = self.sf.list()
        self.assertIn("l1", listing["projects"])
        self.assertIn("l2", listing["projects"])
        detail = self.sf.list("l1")
        self.assertIn("a.txt", detail["files"])
        self.assertTrue(self.sf.remove("l1")["ok"])
        self.assertNotIn("l1", self.sf.list()["projects"])

    def test_read_file(self):
        self.sf.scaffold("r1", {"x.py": "code"})
        self.assertEqual(self.sf.read("r1", "x.py")["content"], "code")
        self.assertFalse(self.sf.read("r1", "missing.py")["ok"])


if __name__ == "__main__":
    unittest.main()
