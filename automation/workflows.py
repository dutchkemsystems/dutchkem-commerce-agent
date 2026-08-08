"""Workflow engine — reusable multi-step automation workflows."""

from typing import Any, Callable, Dict, List, Optional


class WorkflowEngine:
    """Runs named workflows built from ordered steps."""

    def __init__(self):
        self.workflows: Dict[str, Dict] = {}

    def register(self, name: str, steps: List[Dict]):
        """Register a workflow. Each step: {name, action, kwargs}."""
        self.workflows[name] = {"name": name, "steps": steps}

    def run(self, name: str, context: Optional[Dict] = None) -> Dict:
        if name not in self.workflows:
            return {"ok": False, "error": f"workflow '{name}' not found"}
        context = dict(context or {})
        results = {}
        for step in self.workflows[name]["steps"]:
            action = step.get("action")
            if not callable(action):
                results[step.get("name", "step")] = {
                    "error": "step has no callable action",
                    "spec": step,
                }
                continue
            try:
                results[step.get("name", "step")] = action(**step.get("kwargs", {}))
            except Exception as exc:  # noqa: BLE001
                results[step.get("name", "step")] = {"error": str(exc)}
        return {"ok": True, "workflow": name, "results": results}
