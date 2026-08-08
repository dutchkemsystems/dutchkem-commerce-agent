"""Fleet Commander Agent — LLM-driven orchestration and project management."""

from agents.base_agent import BaseAgent

SYSTEM_PROMPT = """You are the Fleet Commander Agent, an expert in multi-agent orchestration.

You coordinate multiple agents to complete complex tasks:

1. Task Decomposition:
   - Break down large tasks into sub-tasks
   - Identify dependencies
   - Create an execution plan

2. Agent Assignment:
   - Assign tasks to appropriate agents
   - Balance workload
   - Handle agent failures

3. Parallel Execution:
   - Execute multiple agents concurrently
   - Monitor progress
   - Sync results

4. Communication:
   - Agent-to-agent communication
   - Status updates
   - Issue escalation

5. Quality Control:
   - Review agent outputs
   - Verify completeness
   - Ensure consistency

6. Audit Trail:
   - Track all agent actions
   - Record decisions
   - Store results

Your coordination must be efficient, fault-tolerant, transparent, and scalable.
Provide execution plans and progress reports."""


class FleetCommanderAgent(BaseAgent):
    def __init__(self, **kwargs):
        super().__init__(
            name="Fleet Commander",
            description="multi-agent orchestration and project management",
            system_prompt=SYSTEM_PROMPT,
            **kwargs,
        )

    def plan(self, task_description: str) -> dict:
        """Produce a deterministic fallback execution plan."""
        return {
            "task": task_description,
            "plan": [
                {"step": 1, "agent": "architect", "action": "design system architecture"},
                {"step": 2, "agent": "coder", "action": "implement components"},
                {"step": 3, "agent": "reviewer", "action": "review code"},
                {"step": 4, "agent": "qa", "action": "test and verify"},
                {"step": 5, "agent": "devops", "action": "deploy"},
            ],
        }
