"""Fleet Commander — orchestration engine for parallel multi-agent execution."""

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class FleetCommander:
    """Registers agents, decomposes tasks, and executes them in parallel.

    Every lifecycle event is recorded to an in-memory audit log and — when
    ``audit_path`` is given — appended to a JSONL file so orchestration history
    survives restarts.
    """

    def __init__(self, max_workers: int = 8, audit_path: str = None):
        self.agents: dict[str, Any] = {}
        self.max_workers = max_workers
        self.audit_log: list[dict[str, Any]] = []
        self.audit_path = Path(audit_path) if audit_path else None
        if self.audit_path:
            self.audit_path.parent.mkdir(parents=True, exist_ok=True)

    def register_agent(self, name: str, agent: Any):
        self.agents[name] = agent
        self._log("agent_registered", {"name": name})

    def execute_task(self, task_description: str) -> dict:
        plan = self._decompose(task_description)
        assignments = self._assign(plan)
        results = self._execute_parallel(assignments)
        merged = self._merge(results, task_description)
        final = self._finalize(merged)
        return final

    def _decompose(self, task_description: str) -> list[dict]:
        architect = self.agents.get("architect")
        if architect is not None and hasattr(architect, "plan"):
            plan = architect.plan(task_description)
            if isinstance(plan, dict) and plan.get("plan"):
                return plan["plan"]
        if architect is not None:
            sub_tasks = architect.generate(task_description)
            return [{"step": 1, "agent": "coder", "action": sub_tasks}]
        return [{"step": 1, "agent": "coder", "action": task_description}]

    def _assign(self, plan: list[dict]) -> dict[str, list[dict]]:
        assignments: dict[str, list[dict]] = {}
        for step in plan:
            agent_name = step.get("agent", "coder")
            assignments.setdefault(agent_name, []).append(step)
        return assignments

    def _execute_parallel(self, assignments: dict[str, list[dict]]) -> dict[str, list]:
        results: dict[str, list] = {}
        with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
            futures = {}
            for agent_name, tasks in assignments.items():
                agent = self.agents.get(agent_name)
                if agent is None:
                    results[agent_name] = [{"error": f"agent '{agent_name}' not registered"}]
                    continue
                futures[pool.submit(agent.generate, self._tasks_to_prompt(tasks))] = agent_name
            for future in as_completed(futures):
                agent_name = futures[future]
                try:
                    results[agent_name] = [{"output": future.result()}]
                except Exception as exc:  # noqa: BLE001
                    results[agent_name] = [{"error": str(exc)}]
        self._log("parallel_execution", {k: len(v) for k, v in results.items()})
        return results

    def _merge(self, results: dict[str, list], task: str) -> dict:
        return {
            "task": task,
            "agents_used": list(results.keys()),
            "agent_results": results,
            "timestamp": datetime.now(UTC).isoformat(),
        }

    def _finalize(self, merged: dict) -> dict:
        combined = []
        for agent_name, items in merged["agent_results"].items():
            for item in items:
                if "output" in item:
                    combined.append(f"[{agent_name}]\n{item['output']}")
                elif "error" in item:
                    combined.append(f"[{agent_name}] ERROR: {item['error']}")
        merged["combined_output"] = "\n\n".join(combined)
        merged["audit_trail"] = list(self.audit_log)
        return merged

    @staticmethod
    def _tasks_to_prompt(tasks: list[dict]) -> str:
        lines = []
        for t in tasks:
            action = t.get("action", t.get("description", ""))
            lines.append(f"- {action}")
        return "Execute the following assigned tasks:\n" + "\n".join(lines)

    def _log(self, event: str, payload: dict):
        entry = {
            "event": event,
            "payload": payload,
            "timestamp": datetime.now(UTC).isoformat(),
        }
        self.audit_log.append(entry)
        if self.audit_path:
            try:
                with open(self.audit_path, "a", encoding="utf-8") as fh:
                    fh.write(json.dumps(entry) + "\n")
            except OSError:
                pass
