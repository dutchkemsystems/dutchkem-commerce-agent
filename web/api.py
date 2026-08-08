"""REST API for Dutchkem Model 4.0 (Flask).

Run standalone:  python -m web.api
"""

import json
import os
import sys
from pathlib import Path

from flask import Flask, jsonify, request

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator_v4 import DutchkemModel4

_model = None


def get_model() -> DutchkemModel4:
    global _model
    if _model is None:
        _model = DutchkemModel4()
    return _model


def create_api() -> Flask:
    app = Flask(__name__)
    model = get_model()

    @app.get("/")
    def index():
        return jsonify(
            {
                "name": "Dutchkem Model 4.0",
                "version": DutchkemModel4.VERSION,
                "endpoints": ["/api/v1/generate", "/api/v1/agents", "/api/v1/health"],
            }
        )

    @app.get("/api/v1/health")
    def health():
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
        return jsonify({"agents": list(model.agents.keys())})

    @app.get("/api/v1/providers")
    def providers():
        return jsonify(model.llm_status())

    @app.post("/api/v1/model")
    def set_model_ep():
        data = request.get_json(silent=True) or {}
        provider = data.get("provider")
        model_name = data.get("model")
        if not provider and not model_name:
            return jsonify({"error": "provide 'provider' or 'model'"}), 400
        return jsonify(model.set_llm(provider, model_name))

    @app.post("/api/v1/generate")
    def generate():
        data = request.get_json(silent=True) or {}
        prompt = data.get("prompt", "")
        intent = data.get("intent")
        if not prompt:
            return jsonify({"error": "'prompt' is required"}), 400
        if data.get("provider") or data.get("model"):
            model.set_llm(data.get("provider"), data.get("model"))
        if intent:
            result = model.process_request(f"/{intent} {prompt}")
        else:
            result = model.process_request(prompt)
        return jsonify(result)

    return app


if __name__ == "__main__":
    app = create_api()
    port = int(os.getenv("API_PORT") or os.getenv("PORT") or "8000")
    print(f"🔌 REST API at http://localhost:{port}")
    app.run(host="0.0.0.0", port=port)
