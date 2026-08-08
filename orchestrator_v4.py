#!/usr/bin/env python3
"""Dutchkem Model 4.0 — The Ultimate AI Build System.

Integrates ALL improvements and features across versions 1.0-4.0:
13 specialized agents, orchestration, persistent memory, security framework,
full SDLC, performance analysis, sandboxed execution, plugins, voice, and
self-improvement.

Usage:
    python orchestrator_v4.py              # CLI
    python orchestrator_v4.py --web        # Gradio web UI
    python orchestrator_v4.py "request"    # one-shot request
"""

import json
import os
import sys
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from agents.system_architect import SystemArchitectAgent
from agents.architect_agent import ArchitectAgent
from agents.coder_agent import CoderAgent
from agents.reviewer_agent import ReviewerAgent
from agents.qa_agent import QAAgent
from agents.devops_agent import DevOpsAgent
from agents.security_agent import SecurityComplianceAgent
from agents.mobile_agent import MobileAgent
from agents.cloud_agent import CloudAgent
from agents.os_kernel_agent import OSKernelAgent
from agents.game_developer_agent import GameDeveloperAgent
from agents.design_agent import DesignAgent
from agents.fleet_commander import FleetCommanderAgent

from fleet.fleet_commander import FleetCommander
from sdlc.sdlc_manager import SDLCManager
from security.security_framework import SecurityFramework
from performance.performance_optimizer import PerformanceOptimizer
from memory.persistent_memory import PersistentMemory
from execution.sandbox_enterprise import EnterpriseSandbox
from tools.browser import BuiltInBrowser
from automation.workflows import WorkflowEngine
from ecosystem.plugin_manager import PluginManager
from enterprise.team_features import TeamManager
from evolution.self_improvement import SelfImprovementEvolution
from voice.voice_assistant import VoiceAssistant

from agents.llm_client import PROVIDER_ORDER, PROVIDERS, _normalize_provider


class DutchkemModel4:
    """The complete orchestrator wiring every agent and subsystem together."""

    VERSION = "4.0.0"

    def __init__(self):
        print("🚀 Initializing Dutchkem Model 4.0...")

        self.architect = SystemArchitectAgent()
        self.planner = ArchitectAgent()
        self.coder = CoderAgent()
        self.reviewer = ReviewerAgent()
        self.qa = QAAgent()
        self.devops = DevOpsAgent()
        self.security = SecurityComplianceAgent()
        self.mobile = MobileAgent()
        self.cloud = CloudAgent()
        self.os_kernel = OSKernelAgent()
        self.game_dev = GameDeveloperAgent()
        self.design = DesignAgent()
        self.fleet_commander = FleetCommanderAgent()

        self.sdlc_manager = SDLCManager()
        self.security_framework = SecurityFramework()
        self.performance_optimizer = PerformanceOptimizer()
        self.fleet = FleetCommander(max_workers=8)

        self.memory = PersistentMemory("dutchkem_global", path=os.getenv("MEMORY_PATH"))
        self.browser = BuiltInBrowser()
        self.workflows = WorkflowEngine()
        self.plugins = PluginManager()
        self.sandbox = EnterpriseSandbox(
            timeout=int(os.getenv("SANDBOX_TIMEOUT", "60")),
            allow_network=os.getenv("SANDBOX_ALLOW_NETWORK", "false").lower() == "true",
        )
        self.team_manager = TeamManager()
        self.evolution = SelfImprovementEvolution(log_path=os.getenv("EVOLUTION_LOG_PATH"))
        self.voice = VoiceAssistant()

        self.agents = {
            "architect": self.architect,
            "planner": self.planner,
            "coder": self.coder,
            "reviewer": self.reviewer,
            "qa": self.qa,
            "devops": self.devops,
            "security": self.security,
            "mobile": self.mobile,
            "cloud": self.cloud,
            "os_kernel": self.os_kernel,
            "game_dev": self.game_dev,
            "design": self.design,
            "fleet_commander": self.fleet_commander,
        }
        for name, agent in self.agents.items():
            self.fleet.register_agent(name, agent)

        self.current_project = None
        self.is_running = True
        print(f"✅ Dutchkem Model 4.0 initialized (v{self.VERSION})")
        print(f"📊 Agents registered: {len(self.agents)}")

    @staticmethod
    def _has_keyword(text: str, keyword: str) -> bool:
        import re
        return re.search(r"\b" + re.escape(keyword) + r"\b", text) is not None

    def llm_status(self) -> dict:
        """Report the active LLM provider and the full provider registry."""
        return self.architect.llm.status()

    def set_llm(self, provider: str = None, model: str = None) -> dict:
        """Switch every agent to another provider and/or model at runtime."""
        result = self.architect.llm.set_model(provider, model)
        for name, agent in self.agents.items():
            agent.llm.set_model(result["provider"], result["model"])
            agent.model = agent.llm.model
        return result

    def classify_request(self, user_input: str) -> str:
        lower = user_input.lower()
        if any(self._has_keyword(lower, k) for k in
               ["architecture", "architect", "design the system", "plan the system",
                "microservices", "system design"]):
            return "architecture"
        if any(self._has_keyword(lower, k) for k in
               ["wireframe", "mockup", "ui", "ux", "design system", "prototype", "palette"]):
            return "design"
        if any(self._has_keyword(lower, k) for k in
               ["kernel", "operating system", "driver", "bootloader", "os module", "filesystem"]):
            return "os_kernel"
        if any(self._has_keyword(lower, k) for k in
               ["game", "engine", "platformer", "rpg"]):
            return "game"
        if any(self._has_keyword(lower, k) for k in
               ["security", "vulnerability", "scan", "compliance", "audit", "owasp"]):
            return "security"
        if any(self._has_keyword(lower, k) for k in
               ["performance", "optimize", "speed up", "scalability", "complexity"]):
            return "performance"
        if any(self._has_keyword(lower, k) for k in
               ["sdlc", "lifecycle", "full project", "requirements", "deployment pipeline"]):
            return "sdlc"
        if any(self._has_keyword(lower, k) for k in
               ["fleet", "orchestrate", "coordinate", "multiple agents"]):
            return "fleet"
        if any(self._has_keyword(lower, k) for k in
               ["execute", "run this code", "test code", "run python"]):
            return "execute"
        return "general"

    def process_request(self, user_input: str, context: str = None) -> dict:
        """Route a request to the appropriate agent or subsystem."""
        intent = self.classify_request(user_input)
        try:
            result = self._dispatch(intent, user_input, context)
        except Exception as exc:  # noqa: BLE001
            result = {"error": str(exc)}
        result["intent"] = intent
        self.memory.add(user_input, metadata={"intent": intent}, namespace="requests")
        return result

    def _dispatch(self, intent: str, user_input: str, context: str = None) -> dict:
        if intent == "architecture":
            return {"agent": "architect", "response": self.architect.generate(user_input, context)}
        if intent == "design":
            tokens = self.design.design_system()
            return {
                "agent": "design",
                "design_system": tokens,
                "response": self.design.generate(user_input, context),
            }
        if intent == "os_kernel":
            return {"agent": "os_kernel", "response": self.os_kernel.generate(user_input, context)}
        if intent == "game":
            return {"agent": "game_dev", "response": self.game_dev.generate(user_input, context)}
        if intent == "security":
            report = self.security_framework.scan_code(user_input)
            return {
                "agent": "security",
                "static_scan": report,
                "response": self.security.generate(
                    f"Provide a detailed remediation report for:\n{user_input}"
                    f"\n\nStatic scan summary: {json.dumps(report)}",
                    context,
                ),
            }
        if intent == "performance":
            analysis = self.performance_optimizer.analyze_performance(user_input)
            return {"agent": "performance_optimizer", "analysis": analysis}
        if intent == "sdlc":
            return {"agent": "sdlc", "plan": self.sdlc_manager.execute_project(user_input)}
        if intent == "fleet":
            return {"agent": "fleet", "execution": self.fleet.execute_task(user_input)}
        if intent == "execute":
            import re as _re
            code = _re.sub(
                r"^(execute|run this code|run python|run|python)\b\s*",
                "",
                user_input.strip(),
                flags=_re.IGNORECASE,
            )
            return {"agent": "sandbox", "execution": self.sandbox.execute_python(code)}
        remembered = self.memory.recall(user_input)
        return {
            "agent": "fleet",
            "memory_context": remembered,
            "execution": self.fleet.execute_task(
                f"{user_input}\n\nRelevant memory:\n{remembered}" if remembered else user_input
            ),
        }

    def run_cli(self):
        print("\n" + "=" * 60)
        print("🧠 Dutchkem Model 4.0 — CLI Interface")
        print("=" * 60)
        print("Commands: /architect /design /os_kernel /game /security")
        print("          /performance /sdlc /fleet /execute /model /help /exit")
        print("          e.g. /model deepseek  or  /model groq llama-3.3-70b-versatile")
        print("=" * 60 + "\n")
        while self.is_running:
            try:
                line = input("🚀 > ").strip()
                if not line:
                    continue
                if line in ("/exit", "/quit", "/q"):
                    self.is_running = False
                    break
                if line in ("/help", "/h", "?"):
                    self._print_help()
                    continue
                if line in ("/model", "/models"):
                    print(json.dumps(self.llm_status(), indent=2, default=str))
                    continue
                if line.startswith("/model "):
                    self._set_model_command(line[len("/model "):].strip())
                    continue
                if line.startswith("/"):
                    text = line[1:]
                    if text == "voice":
                        self._voice_mode()
                        continue
                    if text == "stats":
                        self._print_stats()
                        continue
                    intent = self.classify_request(text)
                    result = self.process_request(f"/{intent} {text}")
                else:
                    result = self.process_request(line)
                print(json.dumps(result, indent=2, default=str))
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except EOFError:
                print("\n👋 Goodbye!")
                break
            except Exception as exc:  # noqa: BLE001
                print(f"❌ Error: {exc}")

    def _set_model_command(self, spec: str):
        """Handle `/model <provider>[ /model ]` from the CLI."""
        provider, _, model = spec.partition("/")
        provider = provider.strip()
        model = (model.strip() or None) if "/" in spec else None
        if not model and " " in spec:
            provider, _, model = spec.partition(" ")
            provider = provider.strip()
            model = model.strip() or None
        if not provider:
            print(json.dumps(self.llm_status(), indent=2, default=str))
            return
        status = self.set_llm(provider, model)
        print(f"Model -> {status['provider']}/{status['model']} ({status['base_url']}) | keys: {status['keys']}")

    def _voice_mode(self):
        print("🎤 Voice mode — enter a spoken-style command ('back' to exit)")
        while True:
            line = input("🎤 > ").strip()
            if line in ("back", "exit", "quit"):
                return
            intent = self.voice.parse(line)
            result = self.process_request(f"/{intent['intent']} {line}")
            print(json.dumps(result, indent=2, default=str))

    def _print_help(self):
        print("  /architect  — system architecture & design")
        print("  /design     — UI/UX wireframes & design systems")
        print("  /os_kernel  — OS/kernel modules, drivers, bootloaders")
        print("  /game       — games & game engines")
        print("  /security   — vulnerability scan & compliance")
        print("  /performance— performance & scalability analysis")
        print("  /sdlc       — full software development lifecycle")
        print("  /fleet      — multi-agent orchestration")
        print("  /execute    — run Python in the sandbox")
        print("  /model      — show providers;  /model <provider>[ /model] to switch")
        print("  /voice      — voice command mode")
        print("  /stats      — system stats")
        print("  /exit       — quit")

    def _print_stats(self):
        print(json.dumps(
            {
                "agents": list(self.agents.keys()),
                "memory": self.memory.stats(),
                "evolution": self.evolution.stats(),
                "plugins": self.plugins.discover(),
            },
            indent=2,
        ))

    def run_web(self):
        import time as _time
        from web.app import create_app
        app = create_app(self)
        host = os.getenv("WEB_HOST", "0.0.0.0")
        port = int(os.getenv("WEB_PORT") or os.getenv("PORT") or "5000")
        print(f"🌐 Starting web interface at http://localhost:{port}")
        app.launch(
            server_name=host,
            server_port=port,
            prevent_thread_lock=True,
            quiet=True,
        )
        print(f"✅ Gradio UI listening on {host}:{port}")
        try:
            while True:
                _time.sleep(3600)
        except KeyboardInterrupt:
            pass

    def one_shot(self, text: str):
        result = self.process_request(text)
        print(json.dumps(result, indent=2, default=str))


def main():
    args = sys.argv[1:]
    model = DutchkemModel4()
    provider = None
    model_name = None
    show_providers = "--providers" in args
    rest = []
    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--provider" and i + 1 < len(args):
            provider = args[i + 1]
            i += 2
            continue
        if arg == "--model" and i + 1 < len(args):
            value = args[i + 1]
            if "/" in value:
                provider, model_name = value.split("/", 1)
            elif _normalize_provider(value) in PROVIDERS:
                provider = value
            else:
                model_name = value
            i += 2
            continue
        if arg == "--providers":
            i += 1
            continue
        rest.append(arg)
        i += 1
    if provider or model_name:
        status = model.set_llm(provider, model_name)
        print(f"Model -> {status['provider']}/{status['model']} ({status['base_url']}) | keys: {status['keys']}")
    if show_providers:
        print(json.dumps(model.llm_status(), indent=2, default=str))
        return
    if "--web" in rest:
        model.run_web()
    elif rest and not rest[0].startswith("-"):
        model.one_shot(" ".join(rest))
    else:
        model.run_cli()


if __name__ == "__main__":
    main()
