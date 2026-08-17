"""Model Context Protocol (MCP) server for Dutchkem Model 4.0.

Exposes every agent and subsystem as MCP tools so any MCP host (Claude Code,
Cursor, opencode, etc.) can drive the build system.

Requires: pip install "mcp>=1.28,<2"

Run:
    python -m web.mcp_server                 # stdio transport
    mcp run web/mcp_server.py                # via MCP CLI
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

_model = None


def get_model():
    global _model
    if _model is None:
        from orchestrator_v4 import DutchkemModel4
        _model = DutchkemModel4()
    return _model


def build_server():
    """Construct and return the MCP server with Dutchkem tools registered."""
    from mcp.server.fastmcp import FastMCP

    mcp = FastMCP("dutchkem-model-4.0", json_response=True)
    model = get_model()

    @mcp.tool()
    def run_agent(agent: str, prompt: str) -> str:
        """Run a single Dutchkem agent by name.

        Args:
            agent: agent name (architect, planner, coder, reviewer, qa, devops,
                   security, mobile, cloud, os_kernel, game_dev, design,
                   fleet_commander)
            prompt: the task or request for the agent
        """
        target = model.agents.get(agent)
        if target is None:
            return json.dumps({"error": f"unknown agent '{agent}'", "available": list(model.agents)})
        return target.generate(prompt)

    @mcp.tool()
    def route_request(prompt: str, intent: str = None) -> str:
        """Route a natural-language request through the full Dutchkem orchestrator.

        Args:
            prompt: the user request
            intent: optional override (architecture, design, os_kernel, game,
                    security, performance, sdlc, fleet, execute, general)
        """
        result = model.process_request(f"/{intent} {prompt}" if intent else prompt)
        return json.dumps(result, default=str, indent=2)

    @mcp.tool()
    def security_scan(code: str) -> str:
        """Scan code for security vulnerabilities and compliance issues.

        Args:
            code: source code to analyze
        """
        return json.dumps(model.security_framework.scan_code(code), indent=2)

    @mcp.tool()
    def performance_analyze(code: str) -> str:
        """Analyze code for performance and scalability problems.

        Args:
            code: source code to analyze
        """
        return json.dumps(model.performance_optimizer.analyze_performance(code), indent=2)

    @mcp.tool()
    def sdlc_plan(description: str) -> str:
        """Generate a full software development lifecycle plan.

        Args:
            description: project description
        """
        return json.dumps(model.sdlc_manager.execute_project(description), indent=2)

    @mcp.tool()
    def fleet_execute(task: str) -> str:
        """Orchestrate multiple agents in parallel to complete a task.

        Args:
            task: description of the task for the fleet
        """
        return json.dumps(model.fleet.execute_task(task), default=str, indent=2)

    @mcp.tool()
    def execute_python(code: str) -> str:
        """Execute Python code in the isolated sandbox.

        Args:
            code: Python source to run
        """
        return json.dumps(model.sandbox.execute_python(code), indent=2)

    @mcp.tool()
    def build_project(description: str, project: str = None) -> str:
        """Generate a runnable project and write it to disk under generated/.

        Args:
            description: what to build (e.g. 'a REST API with FastAPI and auth')
            project: optional directory name for the project
        """
        return json.dumps(model.build_project(description, project=project), indent=2)

    @mcp.tool()
    def list_projects(project: str = None) -> str:
        """List generated projects (or all files within one project).

        Args:
            project: optional project name to inspect
        """
        return json.dumps(model.scaffolder.list(project), indent=2)

    @mcp.tool()
    def run_workflow(name: str, description: str = "") -> str:
        """Run a named multi-step workflow.

        Args:
            name: workflow name (e.g. build-pipeline, generate)
            description: the task description used as workflow context
        """
        return json.dumps(model.run_workflow(name, description), indent=2)

    @mcp.tool()
    def plugin_run(name: str, arg: str = None) -> str:
        """Invoke a plugin's run() function.

        Args:
            name: plugin name (see list_plugins)
            arg: optional single argument passed to the plugin
        """
        return json.dumps(model.plugin_run(name, arg), indent=2)

    @mcp.tool()
    def list_plugins() -> str:
        """List available and loaded plugins."""
        return json.dumps({"plugins": model.plugins.discover(),
                           "installed": model.plugins.installed()}, indent=2)

    @mcp.tool()
    def memory_store(content: str, namespace: str = "default") -> str:
        """Store a fact in persistent memory.

        Args:
            content: the information to remember
            namespace: optional namespace to store under
        """
        return json.dumps({"id": model.memory.add(content, namespace=namespace)})

    @mcp.tool()
    def memory_search(query: str, k: int = 5) -> str:
        """Search persistent memory for relevant context.

        Args:
            query: what to look for
            k: number of results to return
        """
        return json.dumps(model.memory.search(query, k=k), indent=2)

    @mcp.tool()
    def design_system(primary: str = None) -> str:
        """Generate a design token system (colors, type, spacing).

        Args:
            primary: optional primary color hex
        """
        return json.dumps(model.design.design_system(primary), indent=2)

    @mcp.tool()
    def list_providers() -> str:
        """List all supported LLM providers, their configured key counts, and
        suggested models (DeepSeek, Qwen, Groq, OpenRouter, Mistral, GitHub,
        OpenAI, Anthropic, Ollama)."""
        return json.dumps(model.llm_status(), indent=2)

    @mcp.tool()
    def set_model(provider: str, model: str = None) -> str:
        """Switch every agent to another LLM provider and/or model at runtime.

        Args:
            provider: provider name (deepseek, qwen, groq, openrouter, mistral,
                      github, openai, anthropic, ollama)
            model: optional model name override
        """
        return json.dumps(model.set_llm(provider, model), indent=2)

    @mcp.tool()
    def health() -> str:
        """Report system health: agents, memory, provider availability."""
        return json.dumps({
            "agents": list(model.agents),
            "memory": model.memory.stats(),
            "provider": model.architect.llm.selected_provider,
            "model": model.architect.llm.model,
            "llm_keys": model.architect.llm.key_count,
            "ollama_fallback": model.architect.llm.ollama_auto_fallback,
        }, indent=2)

    return mcp


if __name__ == "__main__":
    server = build_server()
    server.run(transport="stdio")
