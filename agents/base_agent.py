"""Base class shared by every Dutchkem Model 4.0 agent."""

from agents.llm_client import LLMClient


class BaseAgent:
    """An agent wraps an LLM client with a role-specific system prompt."""

    def __init__(
        self,
        name: str,
        description: str,
        system_prompt: str = None,
        model: str = None,
        temperature: float = None,
        llm: LLMClient = None,
    ):
        self.name = name
        self.description = description
        self.llm = llm or LLMClient()
        self.model = model or self.llm.model
        self.temperature = temperature
        self._system_prompt = system_prompt or self._get_system_prompt()

    def _get_system_prompt(self) -> str:
        """Override in subclasses. Defaults to a generic engineering prompt."""
        return (
            f"You are the {self.name} Agent. {self.description}. "
            "Respond with clear, structured, production-quality output."
        )

    @property
    def system_prompt(self) -> str:
        return self._system_prompt

    def generate(self, prompt: str, context: str = None, **kwargs) -> str:
        """Run the agent on a single prompt, optionally with extra context."""
        messages = [{"role": "system", "content": self._system_prompt}]
        if context:
            messages.append({"role": "user", "content": context})
        messages.append({"role": "user", "content": prompt})
        return self.llm.chat(messages, temperature=self.temperature, **kwargs)

    def chat(self, messages: list, **kwargs) -> str:
        """Run the agent over an existing message list."""
        return self.llm.chat(messages, temperature=self.temperature, **kwargs)

    def stream(self, prompt: str, context: str = None):
        """Stream an agent response token by token."""
        messages = [{"role": "system", "content": self._system_prompt}]
        if context:
            messages.append({"role": "user", "content": context})
        messages.append({"role": "user", "content": prompt})
        yield from self.llm.chat_stream(messages, temperature=self.temperature)
