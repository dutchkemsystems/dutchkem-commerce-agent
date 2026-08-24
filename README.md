# 🧠 Dutchkem Model 4.0 — The Ultimate AI Build System

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/dutchkemsystems/dutchkem-commerce-agent)

A self-improving, multi-agent AI build system with **13 specialized agents** and
full-stack tooling: architecture generation, code generation, OS/kernel
development, game development, design/UI-UX, QA, security & compliance, full
SDLC, performance analysis, sandboxed execution, persistent memory, plugins,
voice commands, and a web/REST/CLI interface.

## 🛍️ NEW: WhatsApp AI Commerce Agent

Fully autonomous e-commerce system with:
- **Customer Support** — 24/7 AI-powered support with sentiment analysis
- **E-commerce** — Product catalog, cart, orders, recommendations
- **Payments** — Stripe integration with webhooks and refunds
- **Shipping** — FedEx/UPS with rate shopping and tracking
- **Admin Dashboard** — Complete business management API

→ See [DEPLOY.md](DEPLOY.md) for deployment instructions

## Features

| Area | What it does |
|---|---|
| 13 specialized agents | Architect, System Architect, Coder, Reviewer, QA, DevOps, Security, Mobile, Cloud, OS/Kernel, Game Dev, Design, Fleet Commander |
| Multi-agent orchestration | Parallel execution with `ThreadPoolExecutor`, audit trail, fault handling |
| Full SDLC | requirements → design → development → testing → deployment → maintenance |
| Security & compliance | Static OWASP/SQLi/XSS scanning, GDPR/HIPAA/SOC2/PCI-DSS checks, security score |
| Performance analysis | Time/space complexity heuristics, bottlenecks, optimization suggestions |
| OS/Kernel & games | Expert prompts for kernel modules, drivers, bootloaders, game engines |
| Persistent memory | JSON-backed cross-session memory with similarity recall |
| Sandboxed execution | Runs generated Python in an isolated subprocess or Docker container |
| Self-improvement | Interaction + quality-score logging to `data/evolution.jsonl` |
| Interfaces | CLI, Gradio web UI, Flask REST API, voice command mode |

## Installation

```bash
# Unix
curl -fsSL https://raw.githubusercontent.com/dutchkemsystems/dutchkem-model-4.0/main/install.sh | bash
# or manually
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python scripts/init_knowledge.py

# Windows PowerShell
.\install.ps1
```

Docker (app + local Ollama fallback):

```bash
# one-shot build & run (Gradio UI on :5000, Ollama pulls qwen3-coder)
docker compose up --build

# or just the app image
docker build -t dutchkem-model-4.0 .
docker run -it -p 5000:5000 --env-file .env dutchkem-model-4.0
```

## Configuration

Environment variables (shell/env vars take priority over `.env`):

```dotenv
MODEL_PROVIDER=openai             # openai | anthropic | ollama | deepseek | qwen |
                                  # groq | openrouter | mistral | github
                                  # (auto-detected from whichever keys are set)

OPENAI_API_KEY=sk-...             # OpenAI-compatible key
OPENAI_API_KEYS=sk-1,sk-2,...     # optional pool: keys rotated round-robin with
                                  # automatic failover on 401/403/429/5xx
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o-mini

ANTHROPIC_API_KEY=...             # Anthropic provider (optional)
ANTHROPIC_API_KEYS=sk-ant-1,...   # optional pool (same rotation/failover)
ANTHROPIC_BASE_URL=https://api.anthropic.com
ANTHROPIC_MODEL=claude-3-5-sonnet

OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen3-coder          # local fallback model
OLLAMA_AUTO_FALLBACK=true         # use Ollama when cloud keys fail or are absent

MODEL_TEMPERATURE=0.2
MAX_ATTEMPT_SECONDS=30            # global budget for key rotation/retries
MULTI_PROVIDER_FALLBACK=true      # try every configured provider before Ollama

# Security / ops
RUN_GENERATED_CODE=false          # /build never executes generated code implicitly
API_KEY=                          # bearer token for the REST API (leave empty = open)
API_RATE_LIMIT=120                # max /api/v1 requests per client per window
LOG_LEVEL=INFO                    # dutchkem.* logger level
FLEET_AUDIT_PATH=./data/fleet_audit.jsonl   # JSONL audit trail for fleet runs
```

Works with OpenAI, OpenRouter, Groq, Together, vLLM, LM Studio, Ollama, and
any proxy that exposes OpenAI-compatible or Anthropic endpoints. Example using
the openapis.online proxy (set these in your shell or `.env`):

```powershell
$env:OPENAI_API_KEY   = "admin"
$env:OPENAI_BASE_URL  = "https://api.openapis.online/openai"
$env:ANTHROPIC_API_KEY   = "admin"
$env:ANTHROPIC_BASE_URL  = "https://api.openapis.online/anthropic"
```

Without any key the system runs in **offline/demo mode** (deterministic responses).

### Free & open model providers

The system ships with built-in presets for free model backends — DeepSeek, Qwen
(DashScope), Groq, OpenRouter, Mistral and GitHub Models — all speaking the
OpenAI-compatible API, plus local Ollama for fully-open models. Just set the
matching key(s) in your environment or `.env`:

| Provider | Key env var | Default model | Free signup |
|---|---|---|---|
| DeepSeek | `DEEPSEEK_API_KEY` | `deepseek-chat` | platform.deepseek.com |
| Qwen (Alibaba) | `DASHSCOPE_API_KEY` | `qwen-plus` | bailian.console.aliyun.com |
| Groq | `GROQ_API_KEY` | `llama-3.3-70b-versatile` | console.groq.com |
| OpenRouter | `OPENROUTER_API_KEY` | `google/gemma-4-26b-a4b-it:free` | openrouter.ai |
| Mistral | `MISTRAL_API_KEY` | `open-mistral-nemo` | console.mistral.ai |
| GitHub Models | `GITHUB_TOKEN` | `gpt-4o-mini` | github.com/settings/tokens |
| Ollama (local) | — | `qwen3-coder` | ollama.com |
| OpenAI | `OPENAI_API_KEY` | `gpt-4o-mini` | platform.openai.com |
| Anthropic | `ANTHROPIC_API_KEY` | `claude-3-5-sonnet` | console.anthropic.com |

Each provider accepts `X_API_KEYS` (comma-separated pool) with round-robin
rotation and failover on 401/403/429/5xx. With `MULTI_PROVIDER_FALLBACK=true`
(the default) the client tries the selected provider, then every other
configured provider, then local Ollama, then offline mode — so you stay online
even when one backend goes down.

**Switch backends at runtime** — useful for picking a free model for a big
build, or falling back to local Ollama for private work:

```bash
python orchestrator_v4.py --model deepseek        # switch before one-shot
python orchestrator_v4.py --model groq/llama-3.3-70b-versatile
python orchestrator_v4.py --providers             # list all providers/status
python orchestrator_v4.py --web                   # Gradio "Model" tab
```

CLI: `/model` shows the registry, `/model deepseek` switches, `/model qwen qwen-max`
selects a specific model. REST: `GET /api/v1/providers`, `POST /api/v1/model`.
MCP: `list_providers` / `set_model` tools.
If [Ollama](https://ollama.com) is installed and `OLLAMA_AUTO_FALLBACK=true`, the
system automatically falls back to a local model (default `qwen3-coder`,
Apache-2.0) whenever the cloud keys fail or are absent:

```bash
ollama pull qwen3-coder        # or any model you prefer
```

## MCP Server

All 13 agents and subsystems are exposed as [Model Context Protocol](https://modelcontextprotocol.io)
tools, so any MCP client (Claude Desktop, opencode, Cursor, etc.) can drive the
whole build system:

```bash
python -m web.mcp_server
```

A ready-made `.mcp.json` registers it for MCP-native clients:

```json
{
  "mcpServers": {
    "dutchkem-model-4.0": {
      "command": "python",
      "args": ["-m", "web.mcp_server"],
      "cwd": "."
    }
  }
}
```

## Usage

```bash
python orchestrator_v4.py                  # interactive CLI
python orchestrator_v4.py --web            # Gradio UI at http://localhost:5000
python orchestrator_v4.py "build a REST API"  # one-shot
python orchestrator_v4.py --model deepseek "build an iOS app"   # one-shot w/ provider
python -m web.api                          # REST API at http://localhost:8000
```

CLI commands: `/architect /design /os_kernel /game /security /performance
/sdlc /fleet /execute /model /voice /stats /exit`

REST API:

```bash
curl -X POST http://localhost:8000/api/v1/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Build a microservices e-commerce platform", "intent": "architect"}'

curl http://localhost:8000/api/v1/providers            # list providers + status
curl -X POST http://localhost:8000/api/v1/model \
  -H "Content-Type: application/json" \
  -d '{"provider": "qwen", "model": "qwen-max"}'       # switch backend at runtime
```

## Tests

```bash
python -m pytest tests/ -q          # if pytest installed
python -m unittest discover -s tests
```

## Project structure

```
agents/             13 agents + LLM client + BaseAgent
automation/         workflow engine
ecosystem/          plugin manager + example plugin
enterprise/         team & role management
evolution/          self-improvement logging
execution/          sandbox (subprocess/Docker)
fleet/              parallel orchestration engine
memory/             persistent memory + recall
performance/        performance analysis
sdlc/               SDLC lifecycle manager
security/           security & compliance scanners
tools/              built-in browser
voice/              voice command parser
web/                Gradio UI + Flask REST API
scripts/            knowledge-base seeding
tests/              unit tests
orchestrator_v4.py  the brain — routing + CLI
```

## License

MIT
