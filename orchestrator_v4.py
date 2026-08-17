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
import re
import sys
from pathlib import Path

from logging_setup import get_logger, log_exception

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

log = get_logger("orchestrator")

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from agents.architect_agent import ArchitectAgent
from agents.cloud_agent import CloudAgent
from agents.coder_agent import CoderAgent
from agents.design_agent import DesignAgent
from agents.devops_agent import DevOpsAgent
from agents.fleet_commander import FleetCommanderAgent
from agents.game_developer_agent import GameDeveloperAgent
from agents.llm_client import PROVIDERS, _normalize_provider
from agents.mobile_agent import MobileAgent
from agents.os_kernel_agent import OSKernelAgent
from agents.qa_agent import QAAgent
from agents.reviewer_agent import ReviewerAgent
from agents.security_agent import SecurityComplianceAgent
from agents.system_architect import SystemArchitectAgent
from automation.workflows import WorkflowEngine
from ecosystem.plugin_manager import PluginManager
from enterprise.team_features import TeamManager
from evolution.self_improvement import SelfImprovementEvolution
from execution.project_scaffolder import ProjectScaffolder
from execution.sandbox_enterprise import EnterpriseSandbox
from fleet.fleet_commander import FleetCommander
from memory.persistent_memory import PersistentMemory
from performance.performance_optimizer import PerformanceOptimizer
from sdlc.sdlc_manager import SDLCManager
from security.security_framework import SecurityFramework
from tools.browser import BuiltInBrowser
from voice.voice_assistant import VoiceAssistant


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
        self.fleet = FleetCommander(max_workers=8, audit_path=os.getenv(
            "FLEET_AUDIT_PATH", str(ROOT / "data" / "fleet_audit.jsonl")))

        self.memory = PersistentMemory("dutchkem_global", path=os.getenv("MEMORY_PATH"))
        self.workflows = WorkflowEngine()
        self._lazy_cache = {}

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

        self.sdlc_manager.agents = {
            phase: self.agents[agent_name]
            for phase, agent_name in SDLCManager.PHASE_AGENT_DEFAULT.items()
            if agent_name in self.agents
        }
        self._register_workflows()

        self.current_project = None
        self.is_running = True
        print(f"✅ Dutchkem Model 4.0 initialized (v{self.VERSION})")
        print(f"📊 Agents registered: {len(self.agents)}")

    def _lazy(self, key: str, factory):
        """Memoize expensive subsystem construction until first use."""
        cached = self._lazy_cache.get(key)
        if cached is None:
            cached = factory()
            self._lazy_cache[key] = cached
        return cached

    @property
    def browser(self):
        return self._lazy("browser", lambda: BuiltInBrowser())

    @property
    def plugins(self):
        def _factory():
            mgr = PluginManager()
            mgr.load_all()
            return mgr
        return self._lazy("plugins", _factory)

    @property
    def scaffolder(self):
        return self._lazy("scaffolder",
                          lambda: ProjectScaffolder(base_dir=os.getenv("GENERATED_PATH")))

    @property
    def sandbox(self):
        return self._lazy(
            "sandbox",
            lambda: EnterpriseSandbox(
                timeout=int(os.getenv("SANDBOX_TIMEOUT", "60")),
                allow_network=os.getenv("SANDBOX_ALLOW_NETWORK", "false").lower() == "true",
                max_memory_mb=int(os.getenv("SANDBOX_MEMORY_MB", "256")),
                max_cpu_seconds=int(os.getenv("SANDBOX_CPU_SECONDS", "30")),
            ),
        )

    @property
    def team_manager(self):
        return self._lazy("team_manager", lambda: TeamManager())

    @property
    def evolution(self):
        return self._lazy("evolution",
                          lambda: SelfImprovementEvolution(log_path=os.getenv("EVOLUTION_LOG_PATH")))

    @property
    def voice(self):
        return self._lazy("voice", lambda: VoiceAssistant())

    @staticmethod
    def _has_keyword(text: str, keyword: str) -> bool:
        return re.search(r"\b" + re.escape(keyword) + r"\b", text) is not None

    def llm_status(self) -> dict:
        """Report the active LLM provider and the full provider registry."""
        return self.architect.llm.status()

    def set_llm(self, provider: str = None, model: str = None) -> dict:
        """Switch every agent to another provider and/or model at runtime."""
        result = self.architect.llm.set_model(provider, model)
        for agent in self.agents.values():
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
        if any(self._has_keyword(lower, k) for k in
               ["build", "scaffold", "generate project", "create app",
                "create an app", "make an app", "build an app",
                "project structure", "write the project"]):
            return "build"
        if any(self._has_keyword(lower, k) for k in
               ["plugin", "plugins"]):
            return "plugin"
        if any(self._has_keyword(lower, k) for k in
               ["workflow", "pipeline"]):
            return "workflow"
        return "general"

    @staticmethod
    def _slug(name: str) -> str:
        return re.sub(r"[^A-Za-z0-9._-]+", "_", (name or "").strip())

    @staticmethod
    def _strip_command(text: str) -> str:
        """Strip a leading '/command' prefix from an input string."""
        m = re.match(r"^/(\w+)\s*(.*)$", text.strip(), re.S)
        return m.group(2).strip() if m else text.strip()

    def _register_workflows(self):
        """Register default reusable multi-step workflows."""
        def _prompt(context):
            return (context or {}).get("description", "")
        self.workflows.register("build-pipeline", [
            {"name": "architecture",
             "action": lambda **kw: self.architect.generate(_prompt(kw.get("context"))),
             "description": "System architecture design"},
            {"name": "implementation",
             "action": lambda **kw: self.coder.generate(_prompt(kw.get("context"))),
             "description": "Code implementation"},
            {"name": "review",
             "action": lambda **kw: self.reviewer.generate(_prompt(kw.get("context"))),
             "description": "Implementation review"},
            {"name": "verification",
             "action": lambda **kw: self.qa.generate(_prompt(kw.get("context"))),
             "description": "QA verification"},
        ])
        self.workflows.register("generate", [
            {"name": "plan",
             "action": lambda **kw: self.planner.generate(_prompt(kw.get("context"))),
             "description": "Technical planning"},
            {"name": "code",
             "action": lambda **kw: self.coder.generate(_prompt(kw.get("context"))),
             "description": "Code generation"},
        ])

    def build_project(self, description: str, project: str = None,
                      run_code=None) -> dict:
        """Generate a runnable project from a description and write it to disk.

        Asks the Coder agent for a JSON ``{"files": {...}}`` map, scaffolds it
        into ``generated/<project>/`` and optionally runs the main file in the
        sandbox. Falls back to a deterministic starter project if the LLM
        output is not parseable (e.g. offline mode).

        ``run_code`` is opt-in: when left as ``None`` it is read from the
        ``RUN_GENERATED_CODE`` env var (default ``false``) so generated code is
        never executed implicitly.
        """
        name = project or self._slug(description)[:40] or "untitled"
        spec = self.coder.generate(
            "You are scaffolding a complete, runnable project. "
            "Respond with ONLY a single JSON object of this exact shape:\n"
            '{"files": {"relative/path": "file contents", ...}}\n'
            "Include every file needed to build and run it (source code, "
            "requirements, README, tests). No prose, no markdown fences.\n\n"
            f"Request: {description}"
        )
        manifest = self.scaffolder.scaffold_from_json(spec, name)
        note = None
        if not manifest.get("ok"):
            manifest = self.scaffolder.scaffold(
                name, self.scaffolder.default_project(description, name)
            )
            note = "LLM output was not parseable as a file map; wrote a starter project."
        result = {
            "ok": manifest.get("ok", False),
            "project": manifest.get("project"),
            "root": manifest.get("root"),
            "files": manifest.get("files", []),
            "file_count": manifest.get("file_count", 0),
            "errors": manifest.get("errors", []),
        }
        if note:
            result["note"] = note
            result["fallback"] = True
        should_run = (
            run_code if run_code is not None
            else os.getenv("RUN_GENERATED_CODE", "false").strip().lower() in ("1", "true", "yes")
        )
        if should_run and manifest.get("ok"):
            result["execution"] = self._run_main_file(manifest)
        self.evolution.record(
            description, "build", 1.0 if manifest.get("ok") else 0.5,
            note=f"scaffolded {name}",
        )
        return result

    def _run_main_file(self, manifest: dict) -> dict:
        root = Path(manifest.get("root", ""))
        if not root.exists():
            return {"ok": False, "error": "project root missing"}
        candidates = [f for f in manifest.get("files", [])
                      if f.rsplit("/", 1)[-1] in ("app.py", "main.py", "index.py")]
        if not candidates:
            return {"ok": False, "error": "no main file (app.py/main.py/index.py)"}
        try:
            source = (root / candidates[0]).read_text(encoding="utf-8")
        except OSError as exc:
            return {"ok": False, "error": str(exc)}
        return self.sandbox.execute_python(source)

    def run_workflow(self, name: str, description: str = "") -> dict:
        """Run a named workflow with a description as its run-time context."""
        return self.workflows.run(name, {"description": description})

    def plugin_run(self, name: str, *args, **kwargs) -> dict:
        """Load and invoke a plugin's ``run()`` function safely."""
        try:
            module = self.plugins.load(name)
        except FileNotFoundError as exc:
            return {"ok": False, "error": str(exc)}
        fn = getattr(module, "run", None)
        if not callable(fn):
            return {"ok": False, "error": f"plugin '{name}' has no run() function"}
        try:
            return {"ok": True, "plugin": name, "result": fn(*args, **kwargs)}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "plugin": name, "error": str(exc)}

    def process_request(self, user_input: str, context: str = None) -> dict:
        """Route a request to the appropriate agent or subsystem."""
        intent = self.classify_request(user_input)
        try:
            result = self._dispatch(intent, user_input, context)
        except Exception as exc:  # noqa: BLE001
            log_exception(log, exc, f"dispatching intent='{intent}'")
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
            code = re.sub(
                r"^(execute|run this code|run python|run|python)\b\s*",
                "",
                user_input.strip(),
                flags=re.IGNORECASE,
            )
            return {"agent": "sandbox", "execution": self.sandbox.execute_python(code)}
        if intent == "build":
            text = self._strip_command(user_input)
            return {"agent": "build", "execution": self.build_project(text)}
        if intent == "plugin":
            text = re.sub(r"^plugin(s)?\b", "", self._strip_command(user_input), flags=re.I).strip()
            name, _, arg = text.partition(" ")
            if not name:
                return {"agent": "plugin",
                        "plugins": self.plugins.discover(),
                        "installed": self.plugins.installed()}
            return {"agent": "plugin",
                    "execution": self.plugin_run(name.strip(), (arg.strip() or None))}
        if intent == "workflow":
            text = self._strip_command(user_input)
            parts = text.split(None, 1)
            if parts and parts[0] in self.workflows.workflows:
                name, desc = parts[0], (parts[1] if len(parts) > 1 else "")
            else:
                name, desc = "build-pipeline", text
            return {"agent": "workflow", "execution": self.run_workflow(name, desc)}
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
        print("          /performance /sdlc /fleet /build /workflow /plugins")
        print("          /projects /execute /model /help /exit")
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
                if line.startswith("/projects"):
                    print(json.dumps(self.scaffolder.list(), indent=2, default=str))
                    continue
                if line.startswith("/plugin "):
                    rest = line[len("/plugin "):].strip()
                    name, _, arg = rest.partition(" ")
                    print(json.dumps(self.plugin_run(name.strip(), (arg.strip() or None)),
                                     indent=2, default=str))
                    continue
                if line.startswith("/workflow "):
                    parts = line[len("/workflow "):].split(None, 1)
                    name = parts[0] if parts else "build-pipeline"
                    desc = parts[1] if len(parts) > 1 else ""
                    print(json.dumps(self.run_workflow(name, desc), indent=2, default=str))
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
        print("  /build      — generate a project and write it to generated/")
        print("  /workflow   — run a workflow, e.g. /workflow build-pipeline <desc>")
        print("  /plugins    — list plugins;  /plugin <name> [arg] to run one")
        print("  /projects   — list generated projects")
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
        import socket as _socket
        import time as _time

        from web.app import create_app
        app = create_app(self)
        host = os.getenv("WEB_HOST", "0.0.0.0")
        port = int(os.getenv("WEB_PORT") or os.getenv("PORT") or "5000")

        def _port_free(host: str, port: int) -> bool:
            try:
                with _socket.socket(_socket.AF_INET, _socket.SOCK_STREAM) as sock:
                    sock.setsockopt(_socket.SOL_SOCKET, _socket.SO_REUSEADDR, 1)
                    sock.bind((host, port))
                return True
            except OSError:
                return False

        chosen = port
        if not _port_free(host, port):
            for candidate in range(port + 1, port + 21):
                if _port_free(host, candidate):
                    chosen = candidate
                    break
            if chosen == port:
                raise RuntimeError(
                    f"Port {port} is in use and no free port found in range "
                    f"{port}-{port + 20}. Set WEB_PORT/PORT to a free port."
                )
            print(f"⚠️  Port {port} is in use — starting on port {chosen} instead.")
        print(f"🌐 Starting web interface at http://localhost:{chosen}")
        app.launch(
            server_name=host,
            server_port=chosen,
            prevent_thread_lock=True,
            quiet=True,
        )
        print(f"✅ Gradio UI listening on {host}:{chosen}")
        print(f"   Open http://localhost:{chosen} in your browser")
        try:
            while True:
                _time.sleep(3600)
        except KeyboardInterrupt:
            pass

    def one_shot(self, text: str):
        result = self.process_request(text)
        print(json.dumps(result, indent=2, default=str))


def main():
    from logging_setup import setup_logging
    setup_logging()
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
