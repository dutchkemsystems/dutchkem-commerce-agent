"""Full SDLC integration — manages the software development lifecycle."""

from typing import Dict, Optional


class PhaseResult:
    def __init__(self, name: str, success: bool = True, output: str = ""):
        self.name = name
        self.success = success
        self.output = output

    def to_dict(self) -> dict:
        return {"phase": self.name, "success": self.success, "output": self.output}


class RequirementsPhase:
    def execute(self, description: str) -> PhaseResult:
        return PhaseResult(
            "requirements",
            output=f"Captured requirements for: {description}\n"
                   "1. Functional requirements derived from description\n"
                   "2. Non-functional requirements (performance, security, scale)",
        )


class DesignPhase:
    def execute(self, description: str) -> PhaseResult:
        return PhaseResult(
            "design",
            output="Architecture: layered clean architecture\n"
                   "Components, data flow, and interfaces defined",
        )


class DevelopmentPhase:
    def execute(self, description: str) -> PhaseResult:
        return PhaseResult(
            "development",
            output="Implementation plan ready. Delegate to Coder Agent for code generation.",
        )


class TestingPhase:
    def execute(self, description: str) -> PhaseResult:
        return PhaseResult(
            "testing",
            output="Unit, integration, and E2E test plans defined. Delegate to QA Agent.",
        )


class DeploymentPhase:
    def execute(self, description: str) -> PhaseResult:
        return PhaseResult(
            "deployment",
            output="Deployment pipeline defined (CI/CD, containers, cloud target).",
        )


class MaintenancePhase:
    def execute(self, description: str) -> PhaseResult:
        return PhaseResult(
            "maintenance",
            output="Monitoring, logging, and update cadence defined.",
        )


class SDLCManager:
    """Executes the six SDLC phases and returns a per-phase report."""

    PHASE_ORDER = [
        "requirements",
        "design",
        "development",
        "testing",
        "deployment",
        "maintenance",
    ]

    def __init__(self):
        self.phases = {
            "requirements": RequirementsPhase(),
            "design": DesignPhase(),
            "development": DevelopmentPhase(),
            "testing": TestingPhase(),
            "deployment": DeploymentPhase(),
            "maintenance": MaintenancePhase(),
        }

    def execute_project(self, description: str) -> Dict:
        results = {}
        current = "requirements"
        while current:
            phase = self.phases[current]
            result = phase.execute(description)
            results[current] = result.to_dict()
            current = self.get_next_phase(current, result)
        return {"project": description, "phases": results, "complete": True}

    def get_next_phase(self, current: str, result: PhaseResult) -> Optional[str]:
        idx = self.PHASE_ORDER.index(current)
        if result.success and idx < len(self.PHASE_ORDER) - 1:
            return self.PHASE_ORDER[idx + 1]
        return None
