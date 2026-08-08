Write-Host "==> Dutchkem Model 4.0 installer (Windows PowerShell)"
$ErrorActionPreference = "Stop"

$Python = "python"
if (-not (Get-Command $Python -ErrorAction SilentlyContinue)) {
    throw "Python 3.10+ is required and not found on PATH."
}

Write-Host "==> Creating virtual environment"
python -m venv venv
& .\venv\Scripts\Activate.ps1

Write-Host "==> Upgrading pip"
python -m pip install --upgrade pip

Write-Host "==> Installing dependencies"
python -m pip install -r requirements.txt

Write-Host "==> Initializing knowledge base"
python scripts\init_knowledge.py

Write-Host "==> Done."
Write-Host "    Copy .env.example to .env and set at least one provider key, then run:"
Write-Host "        python orchestrator_v4.py           # CLI"
Write-Host "        python orchestrator_v4.py --web     # Web UI"
Write-Host "        python -m web.api                   # REST API"
Write-Host "        python -m web.mcp_server            # MCP server (stdio)"
Write-Host "    Free providers: DEEPSEEK_API_KEY, DASHSCOPE_API_KEY (Qwen),"
Write-Host "    GROQ_API_KEY, OPENROUTER_API_KEY, MISTRAL_API_KEY, GITHUB_TOKEN,"
Write-Host "    or install Ollama (ollama pull qwen3-coder) for a fully local backend."
