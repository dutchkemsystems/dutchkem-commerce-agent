"""Architect Agent — structured design output for the fleet."""

from agents.system_architect import SYSTEM_PROMPT
from agents.base_agent import BaseAgent


class ArchitectAgent(BaseAgent):
    """Alias agent used by the fleet for task decomposition and planning."""

    def __init__(self, **kwargs):
        super().__init__(
            name="Architect",
            description="system architecture, task decomposition, and technical planning",
            system_prompt=SYSTEM_PROMPT,
            **kwargs,
        )
