# setup_render.ps1 — configure Dutchkem Model 4.0 on Render via the Render API.
#
# Modes:
#   create  : create a new web service for this repo, set env vars, first deploy
#   update  : replace the env vars on an existing service and trigger a deploy
#
# Usage:
#   $env:RENDER_API_KEY = "rnd_..."     # or pass -ApiKey
#   ./scripts/setup_render.ps1 -Mode create
#   ./scripts/setup_render.ps1 -Mode update -ServiceId srv-xxxxx
#
# Provider keys are read from your local .env and pushed as secrets. Values are
# never printed; only key names and masked lengths are shown.

param(
    [string]$ApiKey = $env:RENDER_API_KEY,
    [ValidateSet("create", "update")]
    [string]$Mode = "create",
    [string]$ServiceId = $env:RENDER_SERVICE_ID,
    [string]$Name = "dutchkem-model-4.0",
    [string]$Repo = "https://github.com/dutchkemsystems/dutchkem-model-4.0",
    [string]$Branch = "main",
    [string]$OwnerId = "",
    [switch]$SkipDeploy,
    [string]$EnvFile = ".env"
)

$ErrorActionPreference = "Stop"
if ([string]::IsNullOrWhiteSpace($ApiKey)) {
    throw "No API key. Set `$env:RENDER_API_KEY or pass -ApiKey."
}

$H = @{ Authorization = "Bearer $ApiKey"; "Content-Type" = "application/json" }

function Invoke-Render([string]$Method, [string]$Uri, [object]$Body = $null) {
    try {
        if ($null -eq $Body) {
            return Invoke-RestMethod -Method $Method -Uri $Uri -Headers $H
        }
        return Invoke-RestMethod -Method $Method -Uri $Uri -Headers $H -Body ($Body | ConvertTo-Json -Depth 12)
    } catch {
        Write-Host "Render API error ($Method $Uri): $($_.Exception.Message)" -ForegroundColor Red
        if ($_.ErrorDetails.Message) { Write-Host $_.ErrorDetails.Message -ForegroundColor Red }
        throw
    }
}

# ---- Read .env into a hashtable (KEY -> VALUE), skipping comments/blank ----
function Read-DotEnv([string]$path) {
    $map = @{}
    if (-not (Test-Path -LiteralPath $path)) { return $map }
    foreach ($line in Get-Content -LiteralPath $path) {
        $t = $line.Trim()
        if (-not $t -or $t.StartsWith("#")) { continue }
        $i = $t.IndexOf("=")
        if ($i -le 0) { continue }
        $k = $t.Substring(0, $i).Trim()
        $v = $t.Substring($i + 1).Trim()
        $v = $v.Trim('"').Trim("'")
        if ($k) { $map[$k] = $v }
    }
    return $map
}

# ---- Build the full env-var set (defaults, then overridden by .env) ----
function Build-EnvVars([hashtable]$dotenv) {
    $vars = @{
        PYTHON_VERSION            = "3.11.0"
        WEB_HOST                  = "0.0.0.0"
        MODEL_PROVIDER            = "groq"
        MULTI_PROVIDER_FALLBACK   = "true"
        OLLAMA_AUTO_FALLBACK      = "false"   # no local Ollama on Render
        OLLAMA_MODEL              = "qwen3-coder"
        MODEL_TEMPERATURE         = "0.2"
        MAX_ATTEMPT_SECONDS       = "30"
        SANDBOX_TIMEOUT           = "60"
        SANDBOX_ALLOW_NETWORK     = "false"
        MEMORY_PATH               = "/opt/render/project/src/data/memory"
        KNOWLEDGE_PATH            = "/opt/render/project/src/data/knowledge"
        EVOLUTION_LOG_PATH        = "/opt/render/project/src/data/evolution.jsonl"
        OPENAI_BASE_URL           = "https://api.openai.com/v1"
        OPENAI_MODEL              = "gpt-4o-mini"
        ANTHROPIC_BASE_URL        = "https://api.anthropic.com"
        ANTHROPIC_MODEL           = "claude-3-5-sonnet"
        GROQ_MODEL                = "llama-3.3-70b-versatile"
        OPENROUTER_MODEL          = "google/gemma-4-26b-a4b-it:free"
    }
    # Secret keys — only pushed when present in .env (or keep placeholder empty)
    $secretKeys = @(
        "GROQ_API_KEY", "GROQ_API_KEYS", "OPENROUTER_API_KEY", "OPENROUTER_API_KEYS",
        "DEEPSEEK_API_KEY", "DEEPSEEK_API_KEYS", "DASHSCOPE_API_KEY", "DASHSCOPE_API_KEYS",
        "MISTRAL_API_KEY", "MISTRAL_API_KEYS", "GITHUB_TOKEN", "GITHUB_TOKENS",
        "OPENAI_API_KEY", "OPENAI_API_KEYS", "ANTHROPIC_API_KEY", "ANTHROPIC_API_KEYS"
    )
    foreach ($k in $secretKeys) { if (-not $vars.ContainsKey($k)) { $vars[$k] = "" } }

    # Override with .env values where present
    foreach ($k in $dotenv.Keys) {
        if ($vars.ContainsKey($k) -and $dotenv[$k]) { $vars[$k] = $dotenv[$k] }
    }
    $arr = foreach ($k in $vars.Keys) { @{ key = $k; value = $vars[$k] } }
    return @($arr)
}

# ---- Resolve workspace owner id if not given ----
function Resolve-OwnerId {
    if ($OwnerId) { return $OwnerId }
    try {
        $owners = Invoke-Render -Method Get -Uri "https://api.render.com/v1/owners"
        $candidates = @()
        foreach ($o in @($owners)) {
            if ($o.owner) { $o = $o.owner }
            $candidates += $o
        }
        $team = $candidates | Where-Object { $_.type -eq "team" } | Select-Object -First 1
        if ($team) { return $team.id }
    } catch { }
    throw "Could not auto-detect workspace ownerId. Pass -OwnerId (see dashboard Settings page)."
}

$dotenv = Read-DotEnv -path $EnvFile
$envVars = Build-EnvVars -dotenv $dotenv

Write-Host "Pushing $($envVars.Count) environment variables (values masked):"
foreach ($e in $envVars) {
    $len = [string]$e.value
    $mask = if ($e.value) { "set ($($len.Length) chars)" } else { "EMPTY (set in dashboard)" }
    Write-Host ("  {0,-28} {1}" -f $e.key, $mask)
}

if ($Mode -eq "create") {
    $ownerId = Resolve-OwnerId
    $body = @{
        type      = "web_service"
        name      = $Name
        ownerId   = $ownerId
        repo      = $Repo
        branch    = $Branch
        autoDeploy = "yes"
        envVars   = $envVars
        serviceDetails = @{
            runtime           = "python"
            plan              = "free"
            region            = "oregon"
            numInstances      = 1
            healthCheckPath   = "/"
            envSpecificDetails = @{
                buildCommand = "pip install -r requirements.txt"
                startCommand = "python orchestrator_v4.py --web"
            }
        }
    }
    Write-Host "Creating service '$Name' on Render..."
    $resp = Invoke-Render -Method Post -Uri "https://api.render.com/v1/services" -Body $body
    $svc = $resp.service
    Write-Host ""
    Write-Host "Service created:" -ForegroundColor Green
    Write-Host "  id       : $($svc.id)"
    Write-Host "  name     : $($svc.name)"
    Write-Host "  url      : $($svc.serviceDetails.url)"
    Write-Host "  dashboard: $($svc.dashboardUrl)"
    Write-Host "  deployId : $($resp.deployId)"
    Write-Host "  env vars : $($envVars.Count) applied"
    Write-Host ""
    Write-Host "TIP: free plans can't attach a persistent disk, so memory is ephemeral. Upgrade to a paid plan and add a disk (see render.yaml) to persist it."
} else {
    if ([string]::IsNullOrWhiteSpace($ServiceId)) {
        throw "update mode requires -ServiceId."
    }
    Write-Host "Updating env vars on service $ServiceId ..."
    $null = Invoke-Render -Method Put -Uri "https://api.render.com/v1/services/$ServiceId/env-vars" -Body $envVars
    Write-Host "Env vars updated ($($envVars.Count))."
    if (-not $SkipDeploy) {
        Write-Host "Triggering deploy..."
        $null = Invoke-Render -Method Post -Uri "https://api.render.com/v1/services/$ServiceId/deploys" -Body @{}
        Write-Host "Deploy triggered."
    }
    Write-Host "Done."
}
