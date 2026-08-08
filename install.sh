#!/usr/bin/env bash
set -euo pipefail

echo "==> Dutchkem Model 4.0 installer (Unix)"

PYTHON=${PYTHON:-python3}

echo "==> Creating virtual environment"
"$PYTHON" -m venv venv
source venv/bin/activate

echo "==> Upgrading pip"
pip install --upgrade pip

echo "==> Installing dependencies"
pip install -r requirements.txt

echo "==> Initializing knowledge base"
python scripts/init_knowledge.py

echo "==> Done."
echo "    Copy .env.example to .env and set at least one provider key, then run:"
echo "        python orchestrator_v4.py          # CLI"
echo "        python orchestrator_v4.py --web    # Web UI"
echo "        python -m web.api                  # REST API"
echo "        python -m web.mcp_server           # MCP server (stdio)"
echo "    Free providers: DEEPSEEK_API_KEY, DASHSCOPE_API_KEY (Qwen),"
echo "    GROQ_API_KEY, OPENROUTER_API_KEY, MISTRAL_API_KEY, GITHUB_TOKEN,"
echo "    or install Ollama (ollama pull qwen3-coder) for a fully local backend."
