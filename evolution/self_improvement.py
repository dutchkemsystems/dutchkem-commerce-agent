"""Self-improvement & evolution — logs interactions and evolves prompts."""

import json
import time
from pathlib import Path


class SelfImprovementEvolution:
    """Collect feedback, track quality scores, and persist evolution state."""

    def __init__(self, log_path: str = None):
        self.log_path = Path(
            log_path or (Path(__file__).resolve().parent.parent / "data" / "evolution.jsonl")
        )
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self._entries: list = []

    def record(self, task: str, agent: str, score: float, note: str = ""):
        entry = {
            "timestamp": time.time(),
            "task": task,
            "agent": agent,
            "score": float(score),
            "note": note,
        }
        self._entries.append(entry)
        self._append(entry)

    def _append(self, entry: dict):
        with open(self.log_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry) + "\n")

    def load(self) -> list:
        if not self.log_path.exists():
            return []
        entries = []
        with open(self.log_path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        return entries

    def stats(self) -> dict:
        entries = self.load()
        if not entries:
            return {"interactions": 0, "avg_score": 0.0, "per_agent": {}}
        per_agent = {}
        total = 0.0
        for e in entries:
            total += e.get("score", 0)
            per_agent.setdefault(e.get("agent", "?"), []).append(e.get("score", 0))
        return {
            "interactions": len(entries),
            "avg_score": round(total / len(entries), 3),
            "per_agent": {
                agent: round(sum(s) / len(s), 3) for agent, s in per_agent.items()
            },
        }
