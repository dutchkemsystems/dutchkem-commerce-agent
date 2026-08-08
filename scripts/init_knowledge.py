#!/usr/bin/env python3
"""Initialize the knowledge base with seed documentation."""

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from memory.persistent_memory import PersistentMemory

SEED_DOCS = [
    ("python", "python", "Python 3 syntax, typing (mypy/PEP 484), virtualenv, pip, dataclasses, asyncio."),
    ("web", "python", "FastAPI/Flask REST APIs, DRF, WebSockets, middleware, rate limiting, JWT auth."),
    ("frontend", "python", "React, Next.js, TypeScript, state management, hooks, SSR, styling with Tailwind."),
    ("os", "python", "Linux kernel modules in C, syscalls, /proc, Kconfig/Makefile, drivers, device trees."),
    ("game", "python", "Pygame 2D engine loop, sprite collision, SDL2, ECS architecture for games."),
    ("security", "python", "OWASP Top 10, input validation, password hashing (bcrypt/argon2), TLS."),
    ("cloud", "python", "AWS Lambda, S3, EKS, Terraform, IAM least privilege, auto-scaling, multi-AZ."),
    ("mobile", "python", "Flutter widgets, React Native, SwiftUI, Kotlin Compose, offline caching."),
    ("ai", "python", "LLM agent patterns, tool calling, RAG, vector search (Chroma), fine-tuning."),
    ("sdlc", "python", "Requirements -> design -> development -> testing -> deployment -> maintenance."),
]


def main():
    memory = PersistentMemory("dutchkem_knowledge", path=os.environ.get("KNOWLEDGE_PATH"))
    for namespace, doc_type, content in SEED_DOCS:
        memory.add(content, metadata={"namespace": namespace, "doc_type": doc_type}, namespace=namespace)
    print(f"Seeded {len(SEED_DOCS)} knowledge documents.")
    print(json.dumps(memory.stats(), indent=2))


if __name__ == "__main__":
    main()
