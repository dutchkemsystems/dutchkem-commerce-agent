"""Workflow engine — reusable multi-step automation workflows."""



class WorkflowEngine:
    """Runs named workflows built from ordered steps."""

    def __init__(self):
        self.workflows: dict[str, dict] = {}

    def register(self, name: str, steps: list[dict]):
        """Register a workflow. Each step: {name, action, kwargs}."""
        self.workflows[name] = {"name": name, "steps": steps}

    def run(self, name: str, context: dict | None = None) -> dict:
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
                # The run-time context is always available to a step as the
                # `context` keyword argument; static kwargs may be merged too.
                results[step.get("name", "step")] = action(
                    context=context, **step.get("kwargs", {})
                )
            except TypeError as exc:
                results[step.get("name", "step")] = {
                    "error": f"step signature mismatch: {exc}",
                }
            except Exception as exc:  # noqa: BLE001
                results[step.get("name", "step")] = {"error": str(exc)}
        return {"ok": True, "workflow": name, "results": results}
