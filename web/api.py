"""REST API for Dutchkem Model 4.0 (Flask).

Run standalone:  python -m web.api
"""

import hmac
import logging
import os
import sys
import threading
import time
import uuid
from pathlib import Path

from flask import Flask, g, jsonify, request

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator_v4 import DutchkemModel4

log = logging.getLogger("dutchkem.api")

_model = None


class RateLimiter:
    """Thread-safe sliding-window rate limiter, keyed by client identity."""

    def __init__(self, max_requests: int = 0, window_seconds: float = 60.0):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._hits: dict = {}
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        if not self.max_requests:
            return True
        now = time.time()
        with self._lock:
            timestamps = [t for t in self._hits.get(key, []) if now - t < self.window_seconds]
            if len(timestamps) >= self.max_requests:
                self._hits[key] = timestamps
                return False
            timestamps.append(now)
            self._hits[key] = timestamps
            return True


def build_limiter() -> RateLimiter:
    limit = int(os.getenv("API_RATE_LIMIT", "120"))
    window = float(os.getenv("API_RATE_LIMIT_WINDOW", "60"))
    return RateLimiter(max_requests=limit, window_seconds=window)


def _client_identity() -> str:
    """Best-effort client IP, respecting common proxy headers."""
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.remote_addr or "unknown"


def get_model() -> DutchkemModel4:
    global _model
    if _model is None:
        _model = DutchkemModel4()
    return _model


def _authorized(expected_key: str) -> bool:
    """Constant-time comparison against the configured bearer token."""
    auth = request.headers.get("Authorization", "")
    supplied = ""
    if auth.lower().startswith("bearer "):
        supplied = auth[len("bearer "):].strip()
    elif request.headers.get("X-API-Key"):
        supplied = request.headers.get("X-API-Key", "").strip()
    return bool(expected_key) and hmac.compare_digest(supplied, expected_key)


def create_api() -> Flask:
    app = Flask(__name__)
    rate_limiter = build_limiter()
    api_key = os.getenv("API_KEY", "").strip()

    # The orchestrator is heavy (13 agents); build it lazily on first use so
    # creating the app is cheap and handlers always see the current model.

    if not api_key:
        log.warning(
            "REST API is running WITHOUT authentication (no API_KEY set). "
            "Set API_KEY in the environment to require a bearer token."
        )

    @app.before_request
    def security_middleware():
        request_id = uuid.uuid4().hex[:12]
        g.request_id = request_id
        g._start = time.time()
        if request.path == "/api/v1/health" or not request.path.startswith("/api/v1"):
            return None
        if api_key and not _authorized(api_key):
            return jsonify({"error": "unauthorized",
                            "request_id": request_id}), 401
        if not rate_limiter.allow(_client_identity()):
            return jsonify({"error": "rate limit exceeded",
                            "request_id": request_id}), 429

    @app.after_request
    def audit_middleware(resp):
        duration = time.time() - getattr(g, "_start", time.time())
        req_id = getattr(g, "request_id", "-")
        resp.headers.setdefault("X-Request-ID", req_id)
        log.info(
            "%s %s -> %s (%.0fms) [%s] client=%s",
            request.method, request.path, resp.status_code,
            duration * 1000, req_id, _client_identity(),
        )
        return resp

    @app.get("/")
    def index():
        return jsonify(
            {
                "name": "Dutchkem Model 4.0",
                "version": DutchkemModel4.VERSION,
                "auth": "required" if api_key else "open",
                "warning": None if api_key else "No API_KEY set — API is unauthenticated",
                "endpoints": [
                    "/api/v1/health", "/api/v1/agents", "/api/v1/providers",
                    "/api/v1/model", "/api/v1/generate", "/api/v1/build",
                    "/api/v1/projects", "/api/v1/workflow", "/api/v1/plugins",
                ],
            }
        )

    @app.get("/api/v1/health")
    def health():
        model = get_model()
        return jsonify(
            {
                "status": "ok",
                "agents": len(model.agents),
                "memory": model.memory.stats(),
                "llm_available": model.architect.llm.available,
                "provider": model.architect.llm.selected_provider,
                "model": model.architect.llm.model,
            }
        )

    @app.get("/api/v1/agents")
    def agents():
        return jsonify({"agents": list(get_model().agents.keys())})

    @app.get("/api/v1/providers")
    def providers():
        return jsonify(get_model().llm_status())

    @app.post("/api/v1/model")
    def set_model_ep():
        data = request.get_json(silent=True) or {}
        provider = data.get("provider")
        model_name = data.get("model")
        if not provider and not model_name:
            return jsonify({"error": "provide 'provider' or 'model'"}), 400
        return jsonify(get_model().set_llm(provider, model_name))

    @app.post("/api/v1/generate")
    def generate():
        data = request.get_json(silent=True) or {}
        prompt = data.get("prompt", "")
        intent = data.get("intent")
        if not prompt:
            return jsonify({"error": "'prompt' is required"}), 400
        if data.get("provider") or data.get("model"):
            get_model().set_llm(data.get("provider"), data.get("model"))
        if intent:
            result = get_model().process_request(f"/{intent} {prompt}")
        else:
            result = get_model().process_request(prompt)
        return jsonify(result)

    @app.post("/api/v1/build")
    def build():
        data = request.get_json(silent=True) or {}
        prompt = data.get("prompt", "")
        if not prompt:
            return jsonify({"error": "'prompt' is required"}), 400
        project = data.get("project") or data.get("name")
        if data.get("provider") or data.get("model"):
            get_model().set_llm(data.get("provider"), data.get("model"))
        return jsonify(get_model().build_project(prompt, project=project,
                                             run_code=data.get("run_code")))

    @app.get("/api/v1/projects")
    def projects():
        return jsonify(get_model().scaffolder.list())

    @app.get("/api/v1/projects/<project>")
    def project_files(project):
        return jsonify(get_model().scaffolder.list(project))

    @app.post("/api/v1/workflow")
    def workflow():
        data = request.get_json(silent=True) or {}
        name = data.get("name", "build-pipeline")
        description = data.get("description", data.get("prompt", ""))
        return jsonify(get_model().run_workflow(name, description))

    @app.get("/api/v1/plugins")
    def plugins():
        return jsonify({"plugins": get_model().plugins.discover(),
                        "installed": get_model().plugins.installed()})

    @app.post("/api/v1/plugins/<name>")
    def plugin(name):
        data = request.get_json(silent=True) or {}
        arg = data.get("arg") if "arg" in data else None
        return jsonify(get_model().plugin_run(name, arg))

    return app


if __name__ == "__main__":
    app = create_api()
    port = int(os.getenv("API_PORT") or os.getenv("PORT") or "8000")
    print(f"🔌 REST API at http://localhost:{port}")
    app.run(host="0.0.0.0", port=port)
