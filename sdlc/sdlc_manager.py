"""Full SDLC integration — manages the software development lifecycle.

Each phase can either emit deterministic scaffold output (the default, and
what the unit tests exercise) or — when an agent map is supplied — delegate
to a specialized Dutchkem agent to generate the phase deliverables.
"""



class PhaseResult:
    def __init__(self, name: str, success: bool = True, output: str = ""):
        self.name = name
        self.success = success
        self.output = output

    def to_dict(self) -> dict:
        return {"phase": self.name, "success": self.success, "output": self.output}


class RequirementsPhase:
    def execute(self, description: str, generated: str = None) -> PhaseResult:
        output = generated or (
            f"Captured requirements for: {description}\n"
            "1. Functional requirements derived from description\n"
            "2. Non-functional requirements (performance, security, scale)"
        )
        return PhaseResult("requirements", output=output)


class DesignPhase:
    def execute(self, description: str, generated: str = None) -> PhaseResult:
        output = generated or (
            "Architecture: layered clean architecture\n"
            "Components, data flow, and interfaces defined"
        )
        return PhaseResult("design", output=output)


class DevelopmentPhase:
    def execute(self, description: str, generated: str = None) -> PhaseResult:
        output = generated or (
            "Implementation plan ready. Delegate to Coder Agent for code generation."
        )
        return PhaseResult("development", output=output)


class TestingPhase:
    def execute(self, description: str, generated: str = None) -> PhaseResult:
        output = generated or (
            "Unit, integration, and E2E test plans defined. Delegate to QA Agent."
        )
        return PhaseResult("testing", output=output)


class DeploymentPhase:
    def execute(self, description: str, generated: str = None) -> PhaseResult:
        output = generated or (
            "Deployment pipeline defined (CI/CD, containers, cloud target)."
        )
        return PhaseResult("deployment", output=output)


class MaintenancePhase:
    def execute(self, description: str, generated: str = None) -> PhaseResult:
        output = generated or (
            "Monitoring, logging, and update cadence defined."
        )
        return PhaseResult("maintenance", output=output)


class SDLCManager:
    """Executes the six SDLC phases and returns a per-phase report.

    Pass a dict mapping phase name -> agent (any object with ``generate()``)
    to have each phase produced by a specialized agent instead of the static
    scaffold output.
    """

    PHASE_ORDER = [
        "requirements",
        "design",
        "development",
        "testing",
        "deployment",
        "maintenance",
    ]

    PHASE_AGENT_DEFAULT = {
        "requirements": "architect",
        "design": "design",
        "development": "coder",
        "testing": "qa",
        "deployment": "devops",
        "maintenance": "devops",
    }

    def __init__(self, agents: dict = None):
        self.agents = agents or {}
        self.phases = {
            "requirements": RequirementsPhase(),
            "design": DesignPhase(),
            "development": DevelopmentPhase(),
            "testing": TestingPhase(),
            "deployment": DeploymentPhase(),
            "maintenance": MaintenancePhase(),
        }

    def execute_project(self, description: str) -> dict:
        results = {}
        current = "requirements"
        while current:
            phase = self.phases[current]
            generated = self._generate_phase(current, description)
            result = phase.execute(description, generated=generated)
            results[current] = result.to_dict()
            current = self.get_next_phase(current, result)
        return {"project": description, "phases": results, "complete": True}

    def _generate_phase(self, phase_name: str, description: str) -> str | None:
        agent = self.agents.get(phase_name)
        if agent is None:
            return None
        try:
            return agent.generate(
                f"Produce the {phase_name} phase deliverables (requirements, "
                f"design decisions, artifacts, acceptance criteria) for:\n{description}"
            )
        except Exception:  # noqa: BLE001
            return None

    def get_next_phase(self, current: str, result: PhaseResult) -> str | None:
        idx = self.PHASE_ORDER.index(current)
        if result.success and idx < len(self.PHASE_ORDER) - 1:
            return self.PHASE_ORDER[idx + 1]
        return None
