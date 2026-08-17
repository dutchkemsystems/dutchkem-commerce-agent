"""Tests for Dutchkem Model 4.0 core subsystems.

Run with: python -m pytest tests/ -q   (or python -m unittest discover -s tests)
"""

import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from agents.design_agent import DesignAgent
from agents.fleet_commander import FleetCommanderAgent
from agents.llm_client import (
    PROVIDERS,
    LLMClient,
    _parse_key_pool,
    load_config,
)
from agents.qa_agent import QAAgent
from fleet.fleet_commander import FleetCommander
from memory.persistent_memory import PersistentMemory
from performance.performance_optimizer import PerformanceOptimizer
from sdlc.sdlc_manager import SDLCManager
from security.security_framework import SecurityFramework
from voice.voice_assistant import VoiceAssistant


def _no_keys_config() -> dict:
    """Base config with every provider keyed off so tests never touch the network."""
    cfg = {
        "provider": "openai",
        "temperature": 0.2,
        "max_attempt_seconds": 5,
        "ollama_auto_fallback": False,
        "ollama_base_url": "http://localhost:11434",
        "ollama_model": "qwen3-coder",
    }
    for name in PROVIDERS:
        cfg[f"{name}_api_key"] = ""
        cfg[f"{name}_api_keys"] = []
        cfg[f"{name}_base_url"] = PROVIDERS[name]["default_base_url"]
        cfg[f"{name}_model"] = PROVIDERS[name]["default_model"]
    return cfg


def offline_client() -> LLMClient:
    """A client with no keys so tests never touch the network."""
    return LLMClient(config=_no_keys_config())


class TestMemory(unittest.TestCase):
    def test_add_and_recall(self):
        mem = PersistentMemory("test_mem", path=str(ROOT / "data" / "test"))
        mem.clear()
        mem.add("The capital of France is Paris", namespace="geo")
        hits = mem.search("French capital city", k=3, namespace="geo")
        self.assertTrue(len(hits) >= 1)
        self.assertIn("Paris", hits[0]["content"])
        mem.clear()

    def test_stats(self):
        mem = PersistentMemory("test_mem2", path=str(ROOT / "data" / "test"))
        mem.clear()
        mem.add("hello world", namespace="a")
        self.assertEqual(mem.stats()["total_records"], 1)
        mem.clear()


class TestSecurity(unittest.TestCase):
    def test_injection_detected(self):
        sf = SecurityFramework()
        report = sf.scan_code("def run(cmd):\n    os.system(cmd)\ninnerHTML = x")
        self.assertTrue(report["high_severity_count"] >= 1)

    def test_clean_code(self):
        sf = SecurityFramework()
        report = sf.scan_code("def add(a, b):\n    return a + b")
        self.assertEqual(report["security_score"], 100)


class TestPerformance(unittest.TestCase):
    def test_nested_loops(self):
        po = PerformanceOptimizer()
        analysis = po.analyze_performance("for i in range(n):\n    for j in range(m):\n        x = i*j")
        self.assertIn("nested", analysis["time_complexity"])


class TestSDLC(unittest.TestCase):
    def test_phases_run(self):
        mgr = SDLCManager()
        result = mgr.execute_project("a sample project")
        self.assertEqual(list(result["phases"].keys()), SDLCManager.PHASE_ORDER)
        self.assertTrue(result["complete"])


class TestFleet(unittest.TestCase):
    def test_parallel_execution(self):
        fc = FleetCommander(max_workers=4)
        fc.register_agent("architect", FleetCommanderAgent(llm=offline_client()))
        fc.register_agent("coder", FleetCommanderAgent(llm=offline_client()))
        fc.register_agent("qa", FleetCommanderAgent(llm=offline_client()))
        result = fc.execute_task("build and verify a small feature")
        self.assertIn("coder", result["agents_used"])
        self.assertTrue(result["combined_output"])


class TestVoice(unittest.TestCase):
    def test_parse(self):
        va = VoiceAssistant()
        self.assertEqual(va.parse("please design a system architecture")["intent"], "architecture")
        self.assertEqual(va.intent_to_command("scan for vulnerabilities"), "/security")


class TestQAStatic(unittest.TestCase):
    def test_flags_injection(self):
        qa = QAAgent()
        report = qa.analyze_code_static("def f(x):\n    return eval(x)")
        self.assertTrue(report["flags"])
        self.assertEqual(report["severity"], "HIGH")


class TestDesign(unittest.TestCase):
    def test_palette(self):
        d = DesignAgent()
        tokens = d.design_system(primary="#123456")
        self.assertEqual(tokens["colors"]["primary"], "#123456")
        self.assertIn("spacing", tokens)


class TestLLMClient(unittest.TestCase):
    def test_offline_fallback(self):
        client = offline_client()
        out = client.chat([{"role": "user", "content": "hi"}])
        self.assertIn("offline mode", out)

    def test_provider_auto_detect_openai(self):
        client = LLMClient(config={
            "provider": "",
            "openai_api_key": "abc", "openai_base_url": "https://x/openai", "openai_model": "m",
            "anthropic_api_key": "", "anthropic_base_url": "https://x/anthropic", "anthropic_model": "c",
            "temperature": 0.2,
        })
        self.assertEqual(client.provider, "openai")
        self.assertEqual(client.base_url, "https://x/openai")

    def test_provider_auto_detect_anthropic(self):
        cfg = _no_keys_config()
        cfg["provider"] = ""
        cfg["anthropic_api_key"] = "abc"
        cfg["anthropic_api_keys"] = ["abc"]
        cfg["anthropic_model"] = "c"
        client = LLMClient(config=cfg)
        self.assertEqual(client.provider, "anthropic")
        self.assertEqual(client.model, "c")

    def test_explicit_provider_anthropic(self):
        client = LLMClient(config={
            "provider": "anthropic",
            "openai_api_key": "abc", "openai_base_url": "https://x/openai", "openai_model": "m",
            "anthropic_api_key": "abc", "anthropic_base_url": "https://x/anthropic", "anthropic_model": "c",
            "temperature": 0.2,
        })
        self.assertEqual(client.provider, "anthropic")
        self.assertTrue(client._anthropic_url().endswith("/v1/messages"))

    def test_ollama_config_from_env(self):
        old = dict(os.environ)
        try:
            os.environ["OLLAMA_BASE_URL"] = "http://localhost:9999"
            os.environ["OLLAMA_MODEL"] = "qwen3-coder"
            os.environ["OLLAMA_AUTO_FALLBACK"] = "false"
            cfg = load_config()
            self.assertEqual(cfg["ollama_base_url"], "http://localhost:9999")
            self.assertEqual(cfg["ollama_model"], "qwen3-coder")
            self.assertFalse(cfg["ollama_auto_fallback"])
        finally:
            os.environ.clear()
            os.environ.update(old)

    def test_key_pool_from_env(self):
        old = dict(os.environ)
        try:
            os.environ["OPENAI_API_KEYS"] = "k1,k2, k3 "
            os.environ["OPENAI_API_KEY"] = ""
            os.environ["MODEL_PROVIDER"] = ""
            cfg = load_config()
            self.assertEqual(cfg["openai_api_keys"], ["k1", "k2", "k3"])
            self.assertEqual(cfg["provider"], "openai")
        finally:
            os.environ.clear()
            os.environ.update(old)

    def test_key_pool_parse_fallback(self):
        old = dict(os.environ)
        try:
            os.environ.pop("OPENAI_API_KEYS", None)
            self.assertEqual(_parse_key_pool("OPENAI_API_KEYS", "single"), ["single"])
            os.environ["OPENAI_API_KEYS"] = "a,b"
            self.assertEqual(_parse_key_pool("OPENAI_API_KEYS", "single"), ["a", "b"])
        finally:
            os.environ.clear()
            os.environ.update(old)

    def test_key_rotation_round_robin(self):
        client = LLMClient(config={
            "provider": "openai",
            "openai_api_key": "a", "openai_base_url": "https://x/openai", "openai_model": "m",
            "anthropic_api_key": "", "anthropic_base_url": "https://x/anthropic", "anthropic_model": "c",
            "openai_api_keys": ["a", "b"],
            "temperature": 0.2,
        })
        self.assertEqual(client.key_count, 2)
        first = client._next_key()
        second = client._next_key()
        third = client._next_key()
        self.assertNotEqual(first, second)
        self.assertEqual(first, third)

    def test_provider_ollama_explicit(self):
        client = LLMClient(config={
            "provider": "ollama",
            "openai_api_key": "", "openai_base_url": "https://x/openai", "openai_model": "m",
            "anthropic_api_key": "", "anthropic_base_url": "https://x/anthropic", "anthropic_model": "c",
            "ollama_base_url": "http://localhost:11434", "ollama_model": "qwen3-coder",
            "temperature": 0.2,
        })
        self.assertEqual(client.provider, "ollama")
        self.assertEqual(client.model, "qwen3-coder")
        self.assertFalse(client.available)

    def test_ollama_fallback_disabled_offline(self):
        client = offline_client()
        out = client.chat([{"role": "user", "content": "hi"}])
        self.assertIn("offline mode", out)

    def test_ollama_fallback_enabled_but_unavailable(self):
        import time
        cfg = _no_keys_config()
        cfg["provider"] = "openai"
        cfg["ollama_auto_fallback"] = True
        cfg["ollama_base_url"] = "http://localhost:9"
        cfg["ollama_model"] = "q"
        client = LLMClient(config=cfg)
        client._ollama_cache = (False, time.time())
        out = client.chat([{"role": "user", "content": "hi"}])
        self.assertIn("offline mode", out)

    def test_load_config_deepseek_presets(self):
        old = dict(os.environ)
        try:
            os.environ["DEEPSEEK_API_KEY"] = "sk-ds"
            os.environ["DEEPSEEK_MODEL"] = "deepseek-reasoner"
            os.environ["MODEL_PROVIDER"] = ""
            os.environ["OPENAI_API_KEY"] = ""
            os.environ["OPENAI_API_KEYS"] = ""
            cfg = load_config()
            self.assertEqual(cfg["deepseek_api_key"], "sk-ds")
            self.assertEqual(cfg["deepseek_api_keys"], ["sk-ds"])
            self.assertEqual(cfg["deepseek_model"], "deepseek-reasoner")
            self.assertEqual(cfg["deepseek_base_url"], "https://api.deepseek.com/v1")
            self.assertEqual(cfg["provider"], "deepseek")
        finally:
            os.environ.clear()
            os.environ.update(old)

    def test_auto_detect_from_key_pool(self):
        old = dict(os.environ)
        try:
            os.environ["GROQ_API_KEY"] = "g"
            os.environ["MODEL_PROVIDER"] = ""
            os.environ["OPENAI_API_KEY"] = ""
            os.environ["OPENAI_API_KEYS"] = ""
            cfg = load_config()
            self.assertEqual(cfg["provider"], "groq")
        finally:
            os.environ.clear()
            os.environ.update(old)

    def test_set_model_switches_provider(self):
        cfg = _no_keys_config()
        cfg["provider"] = "openai"
        cfg["deepseek_api_key"] = "k"
        cfg["deepseek_api_keys"] = ["k"]
        client = LLMClient(config=cfg)
        client.set_model("deepseek")
        self.assertEqual(client.provider, "deepseek")
        self.assertEqual(client.model, "deepseek-chat")
        self.assertEqual(client.kind, "openai")
        client.set_model("qwen", "qwen-max")
        self.assertEqual(client.provider, "qwen")
        self.assertEqual(client.model, "qwen-max")
        self.assertEqual(client.selected_provider, "qwen")

    def test_set_model_ollama(self):
        cfg = _no_keys_config()
        cfg["provider"] = "openai"
        client = LLMClient(config=cfg)
        client.set_model("ollama")
        self.assertEqual(client.provider, "ollama")
        self.assertFalse(client.available)

    def test_candidate_provider_order(self):
        cfg = _no_keys_config()
        cfg["provider"] = "openai"
        cfg["openai_api_keys"] = ["a"]
        cfg["deepseek_api_keys"] = ["d"]
        cfg["qwen_api_keys"] = ["q"]
        client = LLMClient(config=cfg)
        names = [s["name"] for s in client._candidate_providers()]
        self.assertEqual(names[0], "openai")
        self.assertIn("deepseek", names)
        client.set_model("deepseek")
        names = [s["name"] for s in client._candidate_providers()]
        self.assertEqual(names[0], "deepseek")

    def test_list_providers_reports_keys(self):
        cfg = _no_keys_config()
        cfg["provider"] = "openai"
        cfg["mistral_api_keys"] = ["m1", "m2"]
        client = LLMClient(config=cfg)
        info = client.list_providers()
        self.assertEqual(info["mistral"]["keys"], 2)
        self.assertEqual(info["current"], "openai")
        self.assertIn("ollama", info)
        self.assertTrue(info["openrouter"]["models"])

    def test_available_false_without_keys(self):
        client = offline_client()
        self.assertFalse(client.available)
        self.assertEqual(client.key_count, 0)

    def test_cross_provider_failover(self):
        cfg = _no_keys_config()
        cfg["provider"] = "openai"
        cfg["openai_api_keys"] = ["a"]
        cfg["deepseek_api_keys"] = ["d"]
        client = LLMClient(config=cfg)
        original = LLMClient._chat_openai
        try:
            def fake_openai(self, messages, temperature, max_tokens, started=None):
                if self.provider == "openai":
                    return "[LLM error: all keys failed — HTTP 503]"
                return "fallback from deepseek"
            LLMClient._chat_openai = fake_openai
            out = client.chat([{"role": "user", "content": "hi"}])
            self.assertEqual(out, "fallback from deepseek")
            self.assertEqual(client.provider, "openai")
        finally:
            LLMClient._chat_openai = original

    def test_multi_provider_fallback_disabled(self):
        cfg = _no_keys_config()
        cfg["provider"] = "openai"
        cfg["openai_api_keys"] = ["a"]
        cfg["deepseek_api_keys"] = ["d"]
        cfg["multi_provider_fallback"] = False
        client = LLMClient(config=cfg)
        self.assertNotIn("deepseek", [s["name"] for s in client._candidate_providers()])


if __name__ == "__main__":
    unittest.main()
