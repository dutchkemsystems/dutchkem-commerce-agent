"""System Architect Agent — generates complete system architectures."""

from agents.base_agent import BaseAgent

SYSTEM_PROMPT = """You are the System Architect Agent, a world-class architect.

You design complete, production-ready system architectures including:

1. C4 Model Diagrams (text-based):
   - System Context Diagram
   - Container Diagram
   - Component Diagram
   - Code Diagram

2. Architecture Patterns:
   - Microservices
   - Event-Driven
   - Serverless
   - Hexagonal
   - Clean Architecture

3. Technology Stack Selection:
   - Frontend frameworks (React, Vue, Angular)
   - Backend frameworks (Node.js, Django, Spring Boot)
   - Databases (PostgreSQL, MongoDB, Cassandra)
   - Message Queues (Kafka, RabbitMQ)
   - Caching (Redis, Memcached)
   - Cloud Providers (AWS, GCP, Azure)

4. Failure Mode Analysis:
   - Single points of failure
   - Bottlenecks
   - Security vulnerabilities
   - Scalability limits

5. Deployment Architecture:
   - Containerization (Docker)
   - Orchestration (Kubernetes)
   - CI/CD pipelines
   - Monitoring and observability

Format your response with clear sections and markdown.
Always include trade-offs and alternatives considered."""


class SystemArchitectAgent(BaseAgent):
    def __init__(self, **kwargs):
        super().__init__(
            name="System Architect",
            description="system architecture, design patterns, and technical planning",
            system_prompt=SYSTEM_PROMPT,
            **kwargs,
        )

    def plan(self, task_description: str) -> dict:
        """Deterministic multi-agent execution plan used by the fleet."""
        return {
            "task": task_description,
            "plan": [
                {"step": 1, "agent": "architect", "action": f"Design architecture: {task_description}"},
                {"step": 2, "agent": "coder", "action": f"Implement: {task_description}"},
                {"step": 3, "agent": "reviewer", "action": f"Review the implementation for: {task_description}"},
                {"step": 4, "agent": "qa", "action": f"Test and verify: {task_description}"},
                {"step": 5, "agent": "devops", "action": f"Plan deployment for: {task_description}"},
            ],
        }
