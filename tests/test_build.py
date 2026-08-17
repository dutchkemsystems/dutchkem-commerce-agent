"""Tests for the /build pipeline, workflows and plugins."""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from orchestrator_v4 import DutchkemModel4  # noqa: E402


class TestBuildProject(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self._old = os.environ.get("GENERATED_PATH")
        os.environ["GENERATED_PATH"] = self.tmp.name
        self.model = DutchkemModel4()

    def tearDown(self):
        if self._old is None:
            os.environ.pop("GENERATED_PATH", None)
        else:
            os.environ["GENERATED_PATH"] = self._old
        self.tmp.cleanup()

    @patch.object(DutchkemModel4, "_run_main_file")
    def test_build_uses_coder_output(self, mock_run):
        mock_run.return_value = {"ok": True}
        manifest = {
            "ok": True,
            "project": "rest_api",
            "files": ["app.py"],
            "file_count": 1,
            "root": str(Path(self.tmp.name) / "rest_api"),
            "errors": [],
        }
        with patch.object(self.model.scaffolder, "scaffold_from_json",
                          return_value=manifest), \
             patch.object(self.model.coder, "generate",
                          return_value=json.dumps({"files": {"app.py": "x"}})):
            result = self.model.build_project("a rest api", project="rest_api", run_code=True)
        self.assertTrue(result["ok"])
        self.assertEqual(result["project"], "rest_api")
        self.assertNotIn("fallback", result)
        mock_run.assert_called_once()

    def test_build_falls_back_to_starter_on_non_json(self):
        with patch.object(self.model.scaffolder, "scaffold_from_json",
                          return_value={"ok": False, "error": "no json"}), \
             patch.object(self.model.scaffolder, "scaffold",
                          return_value={"ok": True, "project": "x", "file_count": 1,
                                        "root": str(Path(self.tmp.name) / "x"),
                                        "files": [], "errors": []}), \
             patch.object(self.model.coder, "generate", return_value="totally not json"):
            result = self.model.build_project("a rest api", run_code=False)
        self.assertTrue(result["ok"])
        self.assertTrue(result["fallback"])
        self.assertIn("note", result)

    def test_build_offline_uses_starter(self):
        with patch.object(self.model.coder, "generate", return_value="not json"):
            result = self.model.build_project("a rest api", project="smoke")
        self.assertTrue(result["ok"])
        self.assertTrue(result["fallback"])
        path = Path(self.tmp.name) / "smoke"
        self.assertTrue(path.exists())

    def test_build_output_dir_from_generated_path(self):
        with patch.object(self.model.coder, "generate", return_value="not json"):
            result = self.model.build_project("a todo api", project="todoapp")
        self.assertEqual(Path(result["root"]).parent, Path(self.tmp.name))

    def test_build_manifest_is_json_serializable(self):
        with patch.object(self.model.coder, "generate", return_value="not json"):
            result = self.model.build_project("an echo server", project="echo")
        json.dumps(result)  # must not raise


class TestWorkflow(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self._old = os.environ.get("GENERATED_PATH")
        os.environ["GENERATED_PATH"] = self.tmp.name
        self.model = DutchkemModel4()

    def tearDown(self):
        if self._old is None:
            os.environ.pop("GENERATED_PATH", None)
        else:
            os.environ["GENERATED_PATH"] = self._old
        self.tmp.cleanup()

    def test_unknown_workflow_returns_error(self):
        result = self.model.run_workflow("does-not-exist", "x")
        self.assertFalse(result["ok"])

    def test_workflow_build_pipeline_runs(self):
        steps = ["architect", "coder", "reviewer", "qa"]
        for name in steps:
            getattr(self.model, name).generate = lambda ctx: "ok"
        result = self.model.run_workflow("build-pipeline", "a demo app")
        self.assertTrue(result["ok"])
        self.assertEqual(result["workflow"], "build-pipeline")
        self.assertEqual(len(result["results"]), 4)


class TestPlugin(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self._old = os.environ.get("GENERATED_PATH")
        os.environ["GENERATED_PATH"] = self.tmp.name
        self.model = DutchkemModel4()

    def tearDown(self):
        if self._old is None:
            os.environ.pop("GENERATED_PATH", None)
        else:
            os.environ["GENERATED_PATH"] = self._old
        self.tmp.cleanup()

    def test_plugins_discover_finds_hello(self):
        self.assertIn("hello", self.model.plugins.discover())

    def test_plugin_run_hello(self):
        result = self.model.plugin_run("hello", "dutch")
        self.assertTrue(result["ok"])
        self.assertEqual(result["plugin"], "hello")
        self.assertIn("Hello, dutch!", result["result"]["message"])

    def test_plugin_unknown(self):
        result = self.model.plugin_run("nope", None)
        self.assertFalse(result["ok"])

    def test_plugin_run_dispatch_in_repl(self):
        result = self.model._dispatch("plugin", "/plugin hello tester")
        self.assertTrue(result["execution"]["ok"])
        self.assertIn("Hello, tester!", result["execution"]["result"]["message"])


if __name__ == "__main__":
    unittest.main()
