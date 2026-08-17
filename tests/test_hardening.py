"""Tests for the hardening improvements: sandbox env scrubbing, API rate
limiting, deferred memory saves, fleet audit persistence, opt-in code execution,
and tolerant JSON extraction."""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from execution.project_scaffolder import ProjectScaffolder  # noqa: E402
from execution.sandbox_enterprise import EnterpriseSandbox  # noqa: E402
from fleet.fleet_commander import FleetCommander  # noqa: E402
from memory.persistent_memory import PersistentMemory  # noqa: E402
from web.api import RateLimiter  # noqa: E402


class TestSandboxEnvScrub(unittest.TestCase):
    def test_api_keys_never_reach_child_env(self):
        old = dict(os.environ)
        try:
            os.environ["OPENAI_API_KEY"] = "sk-super-secret"
            os.environ["GITHUB_TOKEN"] = "ghp-leak"
            os.environ["PATH"] = "/usr/bin:/bin"
            os.environ["HOME"] = "/root"
            sandbox = EnterpriseSandbox(allow_network=False)
            env = sandbox._sanitized_env()
        finally:
            os.environ.clear()
            os.environ.update(old)
        self.assertNotIn("OPENAI_API_KEY", env)
        self.assertNotIn("GITHUB_TOKEN", env)
        self.assertEqual(env.get("PATH"), "/usr/bin:/bin")
        self.assertEqual(env.get("HOME"), "/root")

    def test_docker_command_has_no_network_and_readonly(self):
        # Verify the Docker hardening flags are applied without running docker.
        class _SB(EnterpriseSandbox):
            def _run(self, cmd, timeout, method):
                self.captured_cmd = cmd
                return {"ok": True, "method": method}

        sb = _SB(allow_network=False)
        sb._run_docker("print('hi')", 30)
        cmd = sb.captured_cmd
        self.assertIn("--network", cmd)
        self.assertIn("none", cmd)
        self.assertIn("--read-only", cmd)
        self.assertIn("--cap-drop", cmd)
        self.assertIn("--memory", cmd)
        self.assertIn("--pids-limit", cmd)


class TestRateLimiter(unittest.TestCase):
    def test_allow_until_limit(self):
        lim = RateLimiter(max_requests=2, window_seconds=60)
        self.assertTrue(lim.allow("a"))
        self.assertTrue(lim.allow("a"))
        self.assertFalse(lim.allow("a"))
        self.assertTrue(lim.allow("b"))

    def test_disabled_by_zero(self):
        lim = RateLimiter(max_requests=0)
        self.assertTrue(lim.allow("a"))

    def test_window_expiry(self):
        import time
        lim = RateLimiter(max_requests=1, window_seconds=1)
        self.assertTrue(lim.allow("a"))
        # Simulate an expired window by nudging the recorded timestamps.
        now = time.time()
        with lim._lock:
            lim._hits["a"] = [now - 5]
        self.assertTrue(lim.allow("a"))


class TestMemoryDeferredSave(unittest.TestCase):
    def test_save_deferred_until_flush(self):
        with tempfile.TemporaryDirectory() as tmp:
            mem = PersistentMemory("defer", path=tmp, flush_interval=9999)
            mem.clear()
            mem.add("alpha", namespace="t")
            on_disk = Path(tmp) / "defer.json"
            self.assertEqual(on_disk.read_text(encoding="utf-8").strip(), "[]")
            mem.flush()
            data = __import__("json").loads(on_disk.read_text(encoding="utf-8"))
            self.assertEqual(data[0]["content"], "alpha")
            mem.clear()


class TestFleetAuditPersist(unittest.TestCase):
    def test_events_appended_to_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            fc = FleetCommander(max_workers=1, audit_path=str(Path(tmp) / "audit.jsonl"))
            fc._log("agent_registered", {"name": "architect"})
            fc._log("parallel_execution", {"coder": 1})
            self.assertEqual(len(fc.audit_log), 2)
            lines = (Path(tmp) / "audit.jsonl").read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(lines), 2)
            self.assertIn("agent_registered", lines[0])


class TestBuildCodeOptIn(unittest.TestCase):
    def test_default_does_not_run_code(self):
        from orchestrator_v4 import DutchkemModel4

        with tempfile.TemporaryDirectory() as tmp:
            old_generated = os.environ.get("GENERATED_PATH")
            os.environ["GENERATED_PATH"] = tmp
            old_run = os.environ.pop("RUN_GENERATED_CODE", None)
            model = DutchkemModel4()
            try:
                with patch.object(model.coder, "generate", return_value="not json"), \
                     patch.object(DutchkemModel4, "_run_main_file") as mock_run:
                    result = model.build_project("a demo app", project="optin-check")
                self.assertTrue(result["ok"])
                self.assertNotIn("execution", result)
                mock_run.assert_not_called()
            finally:
                if old_generated is None:
                    os.environ.pop("GENERATED_PATH", None)
                else:
                    os.environ["GENERATED_PATH"] = old_generated
                if old_run is not None:
                    os.environ["RUN_GENERATED_CODE"] = old_run

    def test_explicit_run_code_true_runs(self):
        from orchestrator_v4 import DutchkemModel4

        with tempfile.TemporaryDirectory() as tmp:
            old_generated = os.environ.get("GENERATED_PATH")
            os.environ["GENERATED_PATH"] = tmp
            try:
                model = DutchkemModel4()
                with patch.object(model.coder, "generate", return_value="not json"), \
                     patch.object(DutchkemModel4, "_run_main_file",
                                  return_value={"ok": True}):
                    result = model.build_project("a demo app", project="optin-run",
                                                 run_code=True)
                self.assertIn("execution", result)
            finally:
                if old_generated is None:
                    os.environ.pop("GENERATED_PATH", None)
                else:
                    os.environ["GENERATED_PATH"] = old_generated


class TestTolerantJsonExtraction(unittest.TestCase):
    def test_returns_first_object(self):
        text = 'prefix {"files": {"a.py": "1"}} suffix {"other": 2}'
        data = ProjectScaffolder.extract_json_block(text)
        self.assertIn("files", data)

    def test_nested_string_braces_do_not_break(self):
        text = 'A filter pipe: {"name": "use { and } carefully", "n": 3}'
        data = ProjectScaffolder.extract_json_block(text)
        self.assertEqual(data["name"], "use { and } carefully")
        self.assertEqual(data["n"], 3)

    def test_no_json_returns_empty(self):
        self.assertEqual(ProjectScaffolder.extract_json_block("plain words only"), {})


if __name__ == "__main__":
    unittest.main()
