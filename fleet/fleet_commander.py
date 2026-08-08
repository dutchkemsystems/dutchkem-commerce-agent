"""Fleet Commander — orchestration engine for parallel multi-agent execution."""

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone


class FleetCommander:
    """Registers agents, decomposes tasks, and executes them in parallel."""

    def __init__(self, max_workers: int = 8):
        self.agents: Dict[str, Any] = {}
        self.max_workers = max_workers
        self.audit_log: List[Dict[str, Any]] = []

    def register_agent(self, name: str, agent: Any):
        self.agents[name] = agent
        self._log("agent_registered", {"name": name})

    def execute_task(self, task_description: str) -> Dict:
        plan = self._decompose(task_description)
        assignments = self._assign(plan)
        results = self._execute_parallel(assignments)
        merged = self._merge(results, task_description)
        final = self._finalize(merged)
        return final

    def _decompose(self, task_description: str) -> List[Dict]:
        architect = self.agents.get("architect")
        if architect is not None and hasattr(architect, "plan"):
            plan = architect.plan(task_description)
            if isinstance(plan, dict) and plan.get("plan"):
                return plan["plan"]
        if architect is not None:
            sub_tasks = architect.generate(task_description)
            return [{"step": 1, "agent": "coder", "action": sub_tasks}]
        return [{"step": 1, "agent": "coder", "action": task_description}]

    def _assign(self, plan: List[Dict]) -> Dict[str, List[Dict]]:
        assignments: Dict[str, List[Dict]] = {}
        for step in plan:
            agent_name = step.get("agent", "coder")
            assignments.setdefault(agent_name, []).append(step)
        return assignments

    def _execute_parallel(self, assignments: Dict[str, List[Dict]]) -> Dict[str, List]:
        results: Dict[str, List] = {}
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

    def _merge(self, results: Dict[str, List], task: str) -> Dict:
        return {
            "task": task,
            "agents_used": list(results.keys()),
            "agent_results": results,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def _finalize(self, merged: Dict) -> Dict:
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
    def _tasks_to_prompt(tasks: List[Dict]) -> str:
        lines = []
        for t in tasks:
            action = t.get("action", t.get("description", ""))
            lines.append(f"- {action}")
        return "Execute the following assigned tasks:\n" + "\n".join(lines)

    def _log(self, event: str, payload: Dict):
        self.audit_log.append(
            {"event": event, "payload": payload, "timestamp": datetime.now(timezone.utc).isoformat()}
        )
