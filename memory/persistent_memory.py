"""Persistent Memory System — cross-session memory and RAG."""

import hashlib
import json
import threading
import time
from pathlib import Path
from typing import Any


class PersistentMemory:
    """JSON-backed persistent store with simple vector similarity search.

    Writes are deferred: ``add()`` marks the store dirty and a full-file save
    only happens on ``flush()``, on ``clear()``, or after a ``flush_interval``
    of new records — so bursts of writes don't rewrite the whole file per item.
    """

    def __init__(self, name: str = "dutchkem_global", path: str = None,
                 flush_interval: float = 5.0):
        self.name = name
        base = Path(path or (Path(__file__).resolve().parent.parent / "data" / "memory"))
        self.file = base / f"{name}.json"
        self.file.parent.mkdir(parents=True, exist_ok=True)
        self.flush_interval = flush_interval
        self._records: list[dict[str, Any]] = []
        self._lock = threading.RLock()
        self._dirty = False
        self._last_save = time.time()
        self.load()

    def load(self):
        if self.file.exists():
            try:
                self._records = json.loads(self.file.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                self._records = []

    def save(self):
        """Write the store to disk only if there are pending changes."""
        with self._lock:
            if not self._dirty:
                return
            try:
                self.file.write_text(
                    json.dumps(self._records, indent=2, ensure_ascii=False),
                    encoding="utf-8",
                )
                self._dirty = False
                self._last_save = time.time()
            except OSError:
                pass

    def flush(self):
        """Force a write of any pending changes to disk."""
        self.save()

    def _maybe_flush(self):
        with self._lock:
            stale = time.time() - self._last_save >= self.flush_interval
            if self._dirty and (stale or len(self._records) >= 200):
                self.save()

    def add(self, content: str, metadata: dict = None, namespace: str = "default"):
        doc = {
            "id": hashlib.sha256(content.encode("utf-8")).hexdigest()[:16],
            "content": content,
            "metadata": metadata or {},
            "namespace": namespace,
            "timestamp": time.time(),
        }
        with self._lock:
            for existing in self._records:
                if existing["id"] == doc["id"]:
                    return existing["id"]
            self._records.append(doc)
            self._dirty = True
        self._maybe_flush()
        return doc["id"]

    def search(self, query: str, k: int = 5, namespace: str = None) -> list[dict[str, Any]]:
        """Return the k most similar records using token overlap scoring."""
        q_tokens = set(self._tokenize(query))
        with self._lock:
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

    def history(self, namespace: str = None, limit: int = 50) -> list[dict[str, Any]]:
        with self._lock:
            recs = [
                r for r in self._records
                if namespace is None or r.get("namespace") == namespace
            ]
        recs.sort(key=lambda r: r.get("timestamp", 0), reverse=True)
        return recs[:limit]

    def stats(self) -> dict:
        namespaces = {}
        with self._lock:
            for r in self._records:
                ns = r.get("namespace", "default")
                namespaces[ns] = namespaces.get(ns, 0) + 1
            total = len(self._records)
        return {"total_records": total, "namespaces": namespaces}

    def clear(self):
        with self._lock:
            self._records = []
            self._dirty = True
        self.save()

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        import re
        return re.findall(r"[a-z0-9_]+", text.lower())
