"""Persistent Memory System — cross-session memory and RAG."""

import json
import time
import hashlib
from pathlib import Path
from typing import List, Dict, Any


class PersistentMemory:
    """JSON-backed persistent store with simple vector similarity search."""

    def __init__(self, name: str = "dutchkem_global", path: str = None):
        self.name = name
        base = Path(path or (Path(__file__).resolve().parent.parent / "data" / "memory"))
        self.file = base / f"{name}.json"
        self.file.parent.mkdir(parents=True, exist_ok=True)
        self._records: List[Dict[str, Any]] = []
        self.load()

    def load(self):
        if self.file.exists():
            try:
                self._records = json.loads(self.file.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                self._records = []

    def save(self):
        self.file.write_text(json.dumps(self._records, indent=2, ensure_ascii=False), encoding="utf-8")

    def add(self, content: str, metadata: dict = None, namespace: str = "default"):
        doc = {
            "id": hashlib.sha256(content.encode("utf-8")).hexdigest()[:16],
            "content": content,
            "metadata": metadata or {},
            "namespace": namespace,
            "timestamp": time.time(),
        }
        for existing in self._records:
            if existing["id"] == doc["id"]:
                return existing["id"]
        self._records.append(doc)
        self.save()
        return doc["id"]

    def search(self, query: str, k: int = 5, namespace: str = None) -> List[Dict[str, Any]]:
        """Return the k most similar records using token overlap scoring."""
        q_tokens = set(self._tokenize(query))
        candidates = [
            r for r in self._records
            if namespace is None or r.get("namespace") == namespace
        ]
        scored = []
        for rec in candidates:
            tokens = set(self._tokenize(rec["content"]))
            if not q_tokens:
                score = 0.0
            else:
                score = len(q_tokens & tokens) / len(q_tokens)
            scored.append((score, rec))
        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [rec for _, rec in scored[:k] if _ > 0]

    def recall(self, query: str, k: int = 5, namespace: str = None) -> str:
        hits = self.search(query, k=k, namespace=namespace)
        if not hits:
            return ""
        return "\n---\n".join(h["content"] for h in hits)

    def history(self, namespace: str = None, limit: int = 50) -> List[Dict[str, Any]]:
        recs = [
            r for r in self._records
            if namespace is None or r.get("namespace") == namespace
        ]
        recs.sort(key=lambda r: r.get("timestamp", 0), reverse=True)
        return recs[:limit]

    def stats(self) -> dict:
        namespaces = {}
        for r in self._records:
            ns = r.get("namespace", "default")
            namespaces[ns] = namespaces.get(ns, 0) + 1
        return {"total_records": len(self._records), "namespaces": namespaces}

    def clear(self):
        self._records = []
        self.save()

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        import re
        return re.findall(r"[a-z0-9_]+", text.lower())
