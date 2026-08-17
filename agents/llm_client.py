"""Multi-provider LLM client for Dutchkem Model 4.0.

Speaks any OpenAI-compatible endpoint, Anthropic's API, and local Ollama, with
built-in presets for free/open model providers: DeepSeek, Qwen (DashScope),
Groq, OpenRouter, Mistral, GitHub Models and Ollama. Keys are pooled per
provider with round-robin rotation + failover, and the client automatically
falls back across every configured provider before giving up (then Ollama,
then offline/demo mode).

Reads these environment variables (shell env takes priority over .env):

    MODEL_PROVIDER            openai|anthropic|ollama|deepseek|qwen|groq|
                              openrouter|mistral|github  (auto-detected if unset)
    MODEL_TEMPERATURE         default 0.2
    MAX_ATTEMPT_SECONDS       default 30 (global budget across all providers)
    MULTI_PROVIDER_FALLBACK   true|false — fall back across every configured
                              provider when the selected one fails
    OLLAMA_AUTO_FALLBACK      true|false — fall back to local Ollama last

Per-provider variables (X = provider name, e.g. DEEPSEEK, QWEN, GROQ...):
    X_API_KEY                 single API key
    X_API_KEYS                comma-separated key pool (rotates + failover)
    X_BASE_URL                API base URL
    X_MODEL                   model name
"""

import json
import logging
import os
import threading
import time
from pathlib import Path

from dotenv import load_dotenv

log = logging.getLogger("dutchkem.llm")

try:
    import requests
except ImportError:  # pragma: no cover
    requests = None

# Fallback order used for auto-detection and cross-provider failover.
PROVIDER_ORDER = ["openai", "deepseek", "qwen", "groq", "openrouter", "mistral", "github", "anthropic"]

_ALIASES = {
    "local": "ollama",
    "claude": "anthropic",
    "azure": "openai",
    "openai-compatible": "openai",
    "openai_compatible": "openai",
    "dashscope": "qwen",
    "alibaba": "qwen",
    "githubmodels": "github",
}

# Built-in presets for free/open model providers. All "openai"-kind providers
# expose an OpenAI-compatible /chat/completions endpoint.
PROVIDERS = {
    "openai": {
        "key_env": "OPENAI_API_KEY", "keys_env": "OPENAI_API_KEYS",
        "base_url_env": "OPENAI_BASE_URL", "model_env": "OPENAI_MODEL",
        "default_base_url": "https://api.openai.com/v1", "default_model": "gpt-4o-mini",
        "kind": "openai",
        "models": ["gpt-4o-mini", "gpt-4o", "gpt-4.1-mini"],
    },
    "anthropic": {
        "key_env": "ANTHROPIC_API_KEY", "keys_env": "ANTHROPIC_API_KEYS",
        "base_url_env": "ANTHROPIC_BASE_URL", "model_env": "ANTHROPIC_MODEL",
        "default_base_url": "https://api.anthropic.com", "default_model": "claude-3-5-sonnet",
        "kind": "anthropic",
        "models": ["claude-3-5-sonnet", "claude-3-5-haiku", "claude-sonnet-4-5"],
    },
    "deepseek": {
        "key_env": "DEEPSEEK_API_KEY", "keys_env": "DEEPSEEK_API_KEYS",
        "base_url_env": "DEEPSEEK_BASE_URL", "model_env": "DEEPSEEK_MODEL",
        "default_base_url": "https://api.deepseek.com/v1", "default_model": "deepseek-chat",
        "kind": "openai",
        "models": ["deepseek-chat", "deepseek-reasoner"],
    },
    "qwen": {
        "key_env": "DASHSCOPE_API_KEY", "keys_env": "DASHSCOPE_API_KEYS",
        "base_url_env": "QWEN_BASE_URL", "model_env": "QWEN_MODEL",
        "default_base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "default_model": "qwen-plus",
        "kind": "openai",
        "models": ["qwen-plus", "qwen-turbo", "qwen-max", "qwen-coder-plus", "qwen3-32b"],
    },
    "groq": {
        "key_env": "GROQ_API_KEY", "keys_env": "GROQ_API_KEYS",
        "base_url_env": "GROQ_BASE_URL", "model_env": "GROQ_MODEL",
        "default_base_url": "https://api.groq.com/openai/v1",
        "default_model": "llama-3.3-70b-versatile",
        "kind": "openai",
        "models": ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768", "qwen-2.5-32b"],
    },
    "openrouter": {
        "key_env": "OPENROUTER_API_KEY", "keys_env": "OPENROUTER_API_KEYS",
        "base_url_env": "OPENROUTER_BASE_URL", "model_env": "OPENROUTER_MODEL",
        "default_base_url": "https://openrouter.ai/api/v1",
        "default_model": "google/gemma-4-26b-a4b-it:free",
        "kind": "openai",
        "models": [
            "google/gemma-4-26b-a4b-it:free", "google/gemma-4-31b-it:free",
            "openai/gpt-oss-20b:free", "deepseek/deepseek-chat-v3-0324:free",
            "qwen/qwen-2.5-coder-32b-instruct:free",
        ],
    },
    "mistral": {
        "key_env": "MISTRAL_API_KEY", "keys_env": "MISTRAL_API_KEYS",
        "base_url_env": "MISTRAL_BASE_URL", "model_env": "MISTRAL_MODEL",
        "default_base_url": "https://api.mistral.ai/v1", "default_model": "open-mistral-nemo",
        "kind": "openai",
        "models": ["open-mistral-nemo", "mistral-small-latest", "codestral-latest"],
    },
    "github": {
        "key_env": "GITHUB_TOKEN", "keys_env": "GITHUB_TOKENS",
        "base_url_env": "GITHUB_BASE_URL", "model_env": "GITHUB_MODEL",
        "default_base_url": "https://models.inference.ai.azure.com", "default_model": "gpt-4o-mini",
        "kind": "openai",
        "models": ["gpt-4o-mini", "gpt-4o", "deepseek-r1", "meta-llama-3.1-70b-instruct"],
    },
    "ollama": {
        "key_env": "", "keys_env": "",
        "base_url_env": "OLLAMA_BASE_URL", "model_env": "OLLAMA_MODEL",
        "default_base_url": "http://localhost:11434", "default_model": "qwen3-coder",
        "kind": "ollama",
        "models": ["qwen3-coder", "qwen2.5-coder:32b", "deepseek-coder-v2", "deepseek-r1", "llama3.3", "qwen2.5:14b"],
    },
}


def _normalize_provider(name: str) -> str:
    """Normalize a provider name/alias into a registry key."""
    name = (name or "").strip().lower().replace("-", "_")
    return _ALIASES.get(name, name)


def _parse_key_pool(env_name: str, single_key: str) -> list:
    """Parse a comma-separated key pool; fall back to the single key."""
    raw = os.getenv(env_name, "")
    keys = [k.strip() for k in raw.split(",") if k.strip()]
    if not keys and single_key:
        keys = [single_key]
    return keys


def load_config() -> dict:
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path, override=False)
    else:
        load_dotenv(override=False)
    cfg = {
        "provider": os.getenv("MODEL_PROVIDER", "").strip().lower(),
        "temperature": float(os.getenv("MODEL_TEMPERATURE", "0.2")),
        "max_attempt_seconds": float(os.getenv("MAX_ATTEMPT_SECONDS", "30")),
        "ollama_auto_fallback": os.getenv("OLLAMA_AUTO_FALLBACK", "true").strip().lower() in ("1", "true", "yes"),
        "multi_provider_fallback": os.getenv("MULTI_PROVIDER_FALLBACK", "true").strip().lower() in ("1", "true", "yes"),
    }
    for name, spec in PROVIDERS.items():
        key = os.getenv(spec["key_env"], "").strip() if spec["key_env"] else ""
        cfg[f"{name}_api_key"] = key
        cfg[f"{name}_api_keys"] = _parse_key_pool(spec["keys_env"], key) if spec["keys_env"] else []
        cfg[f"{name}_base_url"] = (
            os.getenv(spec["base_url_env"], spec["default_base_url"]).rstrip("/")
            if spec["base_url_env"] else spec["default_base_url"]
        )
        cfg[f"{name}_model"] = os.getenv(spec["model_env"], spec["default_model"]) if spec["model_env"] else spec["default_model"]
    cfg["provider"] = _resolve_provider(cfg)
    return cfg


def _resolve_provider(cfg: dict) -> str:
    """Explicit MODEL_PROVIDER wins; otherwise auto-detect from available keys."""
    provider = _normalize_provider(cfg.get("provider", ""))
    if provider in PROVIDERS:
        return provider
    if provider:  # unknown explicit name -> treat as OpenAI-compatible
        return "openai"
    for name in PROVIDER_ORDER:
        if cfg.get(f"{name}_api_keys"):
            return name
    return "openai"


class LLMClient:
    """Chat client for OpenAI-compatible, Anthropic and Ollama endpoints."""

    def __init__(self, config: dict = None):
        if config is None:
            config = load_config()
        else:
            merged = load_config()
            for key, value in config.items():
                if value is not None:
                    merged[key] = value
            if "api_key" in config and "openai_api_key" not in config:
                merged["openai_api_key"] = config["api_key"]
                merged["openai_api_keys"] = [config["api_key"]] if config["api_key"] else []
            provided_names = {k: v for k, v in config.items() if v is not None}
            for name in PROVIDERS:
                if f"{name}_api_key" in provided_names and f"{name}_api_keys" not in provided_names:
                    merged[f"{name}_api_keys"] = (
                        [provided_names[f"{name}_api_key"]] if provided_names[f"{name}_api_key"] else []
                    )
            config = merged
            config["provider"] = _resolve_provider(config)
        self.config = config
        self.temperature = self.config["temperature"]
        self.max_attempt_seconds = float(self.config.get("max_attempt_seconds", 30))
        self.ollama_base_url = self.config.get("ollama_base_url", "http://localhost:11434").rstrip("/")
        self.ollama_model = self.config.get("ollama_model", "qwen3-coder")
        self.ollama_auto_fallback = bool(self.config.get("ollama_auto_fallback", True))
        self.multi_provider_fallback = bool(self.config.get("multi_provider_fallback", True))
        self.selected_provider = _normalize_provider(self.config["provider"]) or "openai"
        self._state_lock = threading.RLock()
        self._key_index_lock = threading.Lock()
        self._apply_settings(self._provider_settings(self.selected_provider))
        self._ollama_cache = None

    # ---------- Provider registry / settings ----------

    def _provider_settings(self, name: str) -> dict:
        name = _normalize_provider(name)
        spec = PROVIDERS.get(name, PROVIDERS["openai"])
        keys = list(self.config.get(f"{name}_api_keys") or [])
        base_url = (self.config.get(f"{name}_base_url") or spec["default_base_url"]).rstrip("/")
        model = self.config.get(f"{name}_model") or spec["default_model"]
        return {"name": name, "kind": spec["kind"], "keys": keys, "base_url": base_url, "model": model}

    def _apply_settings(self, s: dict):
        with self._state_lock:
            self.provider = s["name"]
            self.kind = s["kind"]
            self.keys = list(s["keys"])
            self.base_url = s["base_url"].rstrip("/")
            self.model = s["model"]
            self._key_index = 0

    def _restore_selected(self):
        if self.selected_provider in PROVIDERS:
            self._apply_settings(self._provider_settings(self.selected_provider))

    def _candidate_providers(self) -> list:
        """Configured providers (with keys) in fallback order: selected first.

        Ollama is handled separately as the final fallback layer. When
        MULTI_PROVIDER_FALLBACK=false only the selected provider is used.
        """
        if self.provider == "ollama":
            return []
        if not self.multi_provider_fallback:
            names = [self.selected_provider]
        else:
            names = [self.selected_provider] + [p for p in PROVIDER_ORDER if p != self.selected_provider]
        candidates = []
        seen = set()
        for name in names:
            name = _normalize_provider(name)
            if name in seen or name not in PROVIDERS:
                continue
            seen.add(name)
            s = self._provider_settings(name)
            if s["kind"] == "ollama":
                continue
            if s["keys"]:
                candidates.append(s)
        return candidates

    @property
    def available(self) -> bool:
        return requests is not None and bool(self._candidate_providers())

    @property
    def key_count(self) -> int:
        return len(self.keys)

    def _next_key(self) -> str:
        """Round-robin key selection (rotates on each call, thread-safe)."""
        if not self.keys:
            return ""
        with self._key_index_lock:
            key = self.keys[self._key_index % len(self.keys)]
            self._key_index = (self._key_index + 1) % len(self.keys)
        return key

    def _rotate(self):
        """Advance the round-robin key index (thread-safe)."""
        with self._key_index_lock:
            self._key_index = (self._key_index + 1) % len(self.keys) if self.keys else 0

    @staticmethod
    def _retryable(status_code: int) -> bool:
        return status_code in (429, 500, 502, 503, 504)

    # ---------- Runtime provider/model switching ----------

    def set_model(self, provider: str = None, model: str = None) -> dict:
        """Switch to another provider and/or model at runtime. Returns new status."""
        with self._state_lock:
            provider = _normalize_provider(provider or self.selected_provider)
            if provider not in PROVIDERS:
                provider = "openai"
            s = self._provider_settings(provider)
            if model:
                s = dict(s, model=model.strip())
            self.selected_provider = provider
            self._apply_settings(s)
        return self.status()

    def list_providers(self) -> dict:
        """Registry view: each provider's settings, key count and suggested models."""
        out = {}
        for name in list(PROVIDER_ORDER) + ["ollama"]:
            s = self._provider_settings(name)
            out[name] = {
                "kind": s["kind"],
                "base_url": s["base_url"],
                "model": s["model"],
                "keys": len(s["keys"]),
                "models": PROVIDERS.get(name, {}).get("models", []),
            }
        out["current"] = self.selected_provider
        return out

    def status(self) -> dict:
        return {
            "provider": self.selected_provider,
            "model": self.model,
            "base_url": self.base_url,
            "kind": self.kind,
            "keys": self.key_count,
            "available": self.available,
            "providers": self.list_providers(),
        }

    def _budget(self, started: float) -> int:
        """Per-request timeout derived from the remaining attempt budget."""
        remaining = self.max_attempt_seconds - (time.time() - started)
        if remaining <= 0:
            return 0
        return max(1, min(120, int(remaining)))

    def _timeout(self, started: float) -> tuple:
        """(connect, read) timeout — never exceeds the remaining budget."""
        read = self._budget(started)
        if read == 0:
            return (1, 1)
        connect = min(5, max(1, read))
        return (connect, read)

    # ---------- Local Ollama fallback ----------

    def _ollama_available(self) -> bool:
        """True if a local Ollama server is reachable (cached 30s)."""
        if requests is None:
            return False
        now = time.time()
        if self._ollama_cache is not None and now - self._ollama_cache[1] < (
            30 if self._ollama_cache[0] else 5
        ):
            return self._ollama_cache[0]
        ok = False
        try:
            resp = requests.get(f"{self.ollama_base_url}/api/tags", timeout=8)
            ok = resp.status_code == 200
        except Exception:  # noqa: BLE001
            ok = False
        self._ollama_cache = (ok, now)
        return ok

    def _try_ollama(self, messages, temperature=None, max_tokens: int = 2048, stream: bool = False):
        """Attempt a local Ollama chat completion. Returns text, or None on failure."""
        if requests is None or not self._ollama_available():
            return None
        url = f"{self.ollama_base_url}/v1/chat/completions"
        payload = {
            "model": self.ollama_model,
            "messages": messages,
            "temperature": self.temperature if temperature is None else temperature,
            "max_tokens": max_tokens,
            "stream": stream,
        }
        try:
            resp = requests.post(
                url, json=payload,
                headers={"Content-Type": "application/json"},
                timeout=max(60, int(self.max_attempt_seconds)),
            )
            resp.raise_for_status()
            if stream:
                return resp
            return resp.json()["choices"][0]["message"]["content"]
        except Exception:  # noqa: BLE001
            return None

    def _try_ollama_stream(self, messages, temperature=None, max_tokens: int = 2048):
        """Yield Ollama chunks, or a single error chunk if unavailable."""
        resp = self._try_ollama(messages, temperature=temperature, max_tokens=max_tokens, stream=True)
        if resp is None:
            yield "[LLM error: local Ollama unavailable]"
            return
        try:
            for line in resp.iter_lines(decode_unicode=True):
                if not line or not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    return
                try:
                    delta = json.loads(data)["choices"][0]["delta"].get("content", "")
                    if delta:
                        yield delta
                except (json.JSONDecodeError, KeyError, IndexError):
                    continue
        except Exception as exc:  # noqa: BLE001
            yield f"[LLM error: {exc}]"

    # ---------- Public entry points ----------

    def chat(self, messages, temperature: float = None, max_tokens: int = 2048) -> str:
        """Send a chat completion and return the assistant text.

        Fallback order: selected provider -> other configured providers (if
        MULTI_PROVIDER_FALLBACK) -> local Ollama (if enabled) -> offline/demo.
        """
        if self.provider == "ollama":
            local = self._try_ollama(messages, temperature=temperature, max_tokens=max_tokens)
            if local is not None:
                return local
            return self._offline_response(messages)
        candidates = self._candidate_providers()
        if not candidates:
            if self.ollama_auto_fallback:
                local = self._try_ollama(messages, temperature=temperature, max_tokens=max_tokens)
                if local is not None:
                    return local
            log.info("no configured providers — falling back to offline mode")
            return self._offline_response(messages)
        started = time.time()
        first_error = "no providers responded"
        errors = []
        for s in candidates:
            if time.time() - started >= self.max_attempt_seconds:
                first_error = "attempt budget exhausted across providers"
                break
            self._apply_settings(s)
            if s["kind"] == "anthropic":
                result = self._chat_anthropic(messages, temperature, max_tokens, started)
            else:
                result = self._chat_openai(messages, temperature, max_tokens, started)
            if not (isinstance(result, str) and result.startswith("[LLM error")):
                self._restore_selected()
                return result
            errors.append((s["name"], result))
        self._restore_selected()
        if self.ollama_auto_fallback:
            local = self._try_ollama(messages, temperature=temperature, max_tokens=max_tokens)
            if local is not None:
                return local
        if errors:
            def _clean(msg: str) -> str:
                msg = msg.strip()
                if msg.startswith("[LLM error:") and msg.endswith("]"):
                    return msg[len("[LLM error:"):-1].strip()
                return msg
            first_error = f"{_clean(errors[0][1])} (provider '{errors[0][0]}')"
            if len(errors) > 1:
                names = ", ".join(name for name, _ in errors[1:])
                first_error = (
                    f"{first_error}; also tried provider(s): {names} "
                    f"(last error: {_clean(errors[-1][1])})"
                )
        log.warning("all providers failed — %s", first_error)
        return f"[LLM error: {first_error}]"

    def chat_stream(self, messages, temperature: float = None):
        """Yield chunks of a streaming chat completion (with cross-provider + Ollama fallback)."""
        if self.provider == "ollama":
            yield from self._try_ollama_stream(messages, temperature=temperature)
            return
        candidates = self._candidate_providers()
        if not candidates:
            if self.ollama_auto_fallback:
                yield from self._try_ollama_stream(messages, temperature=temperature)
                return
            yield self._offline_response(messages)
            return
        started = time.time()
        for s in candidates:
            if time.time() - started >= self.max_attempt_seconds:
                break
            self._apply_settings(s)
            if s["kind"] == "anthropic":
                gen = self._stream_anthropic(messages, temperature, started)
            else:
                gen = self._stream_openai(messages, temperature, started)
            first = True
            for chunk in gen:
                if first and chunk.startswith("[LLM error"):
                    break
                first = False
                yield chunk
            else:
                self._restore_selected()
                return
        self._restore_selected()
        if self.ollama_auto_fallback:
            yield from self._try_ollama_stream(messages, temperature=temperature)

    # ---------- OpenAI-compatible ----------

    def _chat_openai(self, messages, temperature, max_tokens, started=None) -> str:
        started = started or time.time()
        with self._state_lock:
            url = f"{self.base_url}/chat/completions"
            model = self.model
            keys = list(self.keys)
            key_index = self._key_index
        base_payload = {
            "model": model,
            "messages": messages,
            "temperature": self.temperature if temperature is None else temperature,
            "max_tokens": max_tokens,
        }
        attempts = max(1, len(keys))
        last_error = "no keys configured"
        for offset in range(attempts):
            if time.time() - started >= self.max_attempt_seconds:
                break
            key = keys[(key_index + offset) % len(keys)] if keys else ""
            headers = {
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            }
            try:
                resp = requests.post(url, headers=headers, json=base_payload, timeout=self._timeout(started))
                if resp.status_code in (401, 403) or self._retryable(resp.status_code):
                    self._rotate()
                    last_error = f"HTTP {resp.status_code} ({resp.text[:120]})"
                    continue
                resp.raise_for_status()
                data = resp.json()
                return data["choices"][0]["message"]["content"]
            except Exception as exc:  # noqa: BLE001
                self._rotate()
                last_error = str(exc)
        return f"[LLM error: all keys failed — {last_error}]"

    def _stream_openai(self, messages, temperature, started=None):
        started = started or time.time()
        with self._state_lock:
            url = f"{self.base_url}/chat/completions"
            model = self.model
            keys = list(self.keys)
            key_index = self._key_index
        base_payload = {
            "model": model,
            "messages": messages,
            "temperature": self.temperature if temperature is None else temperature,
            "stream": True,
        }
        attempts = max(1, len(keys))
        last_error = "no keys configured"
        for offset in range(attempts):
            if time.time() - started >= self.max_attempt_seconds:
                break
            key = keys[(key_index + offset) % len(keys)] if keys else ""
            headers = {
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            }
            try:
                with requests.post(url, headers=headers, json=base_payload, stream=True, timeout=self._timeout(started)) as resp:
                    if resp.status_code in (401, 403) or self._retryable(resp.status_code):
                        self._rotate()
                        last_error = f"HTTP {resp.status_code} ({resp.text[:120]})"
                        continue
                    resp.raise_for_status()
                    self._rotate()
                    for line in resp.iter_lines(decode_unicode=True):
                        if not line or not line.startswith("data:"):
                            continue
                        data = line[5:].strip()
                        if data == "[DONE]":
                            return
                        try:
                            delta = json.loads(data)["choices"][0]["delta"].get("content", "")
                            if delta:
                                yield delta
                        except (json.JSONDecodeError, KeyError, IndexError):
                            continue
                    return
            except Exception as exc:  # noqa: BLE001
                self._rotate()
                last_error = str(exc)
        yield f"[LLM error: all keys failed — {last_error}]"

    # ---------- Anthropic ----------

    def _anthropic_url(self) -> str:
        if self.base_url.endswith("/v1"):
            return f"{self.base_url}/messages"
        return f"{self.base_url}/v1/messages"

    @staticmethod
    def _to_anthropic_messages(messages: list):
        """Split OpenAI-style messages into a system prompt + anthropic messages."""
        system_parts = []
        turns = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "system":
                system_parts.append(content)
            else:
                turns.append({"role": role, "content": content})
        system = "\n\n".join(system_parts)
        if turns and turns[0].get("role") == "assistant":
            turns.insert(0, {"role": "user", "content": "(continue)"})
        return system, turns

    def _chat_anthropic(self, messages, temperature, max_tokens, started=None) -> str:
        started = started or time.time()
        system, turns = self._to_anthropic_messages(messages)
        with self._state_lock:
            url = self._anthropic_url()
            model = self.model
            keys = list(self.keys)
            key_index = self._key_index
        base_payload = {
            "model": model,
            "max_tokens": max_tokens,
            "temperature": self.temperature if temperature is None else temperature,
            "messages": turns,
        }
        if system:
            base_payload["system"] = system
        attempts = max(1, len(keys))
        last_error = "no keys configured"
        for offset in range(attempts):
            if time.time() - started >= self.max_attempt_seconds:
                break
            key = keys[(key_index + offset) % len(keys)] if keys else ""
            headers = {
                "x-api-key": key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            }
            try:
                resp = requests.post(url, headers=headers, json=base_payload, timeout=self._timeout(started))
                if resp.status_code in (401, 403) or self._retryable(resp.status_code):
                    self._rotate()
                    last_error = f"HTTP {resp.status_code} ({resp.text[:120]})"
                    continue
                resp.raise_for_status()
                data = resp.json()
                return "".join(block.get("text", "") for block in data.get("content", []))
            except Exception as exc:  # noqa: BLE001
                self._rotate()
                last_error = str(exc)
        return f"[LLM error: all keys failed — {last_error}]"

    def _stream_anthropic(self, messages, temperature, started=None):
        started = started or time.time()
        system, turns = self._to_anthropic_messages(messages)
        with self._state_lock:
            url = self._anthropic_url()
            model = self.model
            keys = list(self.keys)
            key_index = self._key_index
        base_payload = {
            "model": model,
            "max_tokens": 2048,
            "temperature": self.temperature if temperature is None else temperature,
            "messages": turns,
            "stream": True,
        }
        if system:
            base_payload["system"] = system
        attempts = max(1, len(keys))
        last_error = "no keys configured"
        for offset in range(attempts):
            if time.time() - started >= self.max_attempt_seconds:
                break
            key = keys[(key_index + offset) % len(keys)] if keys else ""
            headers = {
                "x-api-key": key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            }
            try:
                with requests.post(
                    url, headers=headers, json=base_payload,
                    stream=True, timeout=self._timeout(started),
                ) as resp:
                    if resp.status_code in (401, 403) or self._retryable(resp.status_code):
                        self._rotate()
                        last_error = f"HTTP {resp.status_code} ({resp.text[:120]})"
                        continue
                    resp.raise_for_status()
                    self._rotate()
                    for line in resp.iter_lines(decode_unicode=True):
                        if not line or not line.startswith("data:"):
                            continue
                        data = line[5:].strip()
                        if data == "[DONE]":
                            return
                        try:
                            event = json.loads(data)
                            if event.get("type") == "content_block_delta":
                                delta = event.get("delta", {}).get("text", "")
                                if delta:
                                    yield delta
                        except json.JSONDecodeError:
                            continue
                    return
            except Exception as exc:  # noqa: BLE001
                self._rotate()
                last_error = str(exc)
        yield f"[LLM error: all keys failed — {last_error}]"

    # ---------- Offline fallback ----------

    def _offline_response(self, messages: list) -> str:
        """Deterministic offline fallback so the system runs without an API key."""
        system = messages[0].get("content", "") if messages else ""
        user = messages[-1].get("content", "") if messages else ""
        name = "Dutchkem Model 4.0"
        if "Architect" in system:
            name = "System Architect Agent"
        elif "Coder" in system:
            name = "Coder Agent"
        elif "QA" in system:
            name = "QA Agent"
        elif "Security" in system:
            name = "Security & Compliance Agent"
        elif "OS/Kernel" in system:
            name = "OS/Kernel Developer Agent"
        elif "Game Developer" in system:
            name = "Game Developer Agent"
        elif "Design Agent" in system:
            name = "Design Agent"
        elif "Fleet Commander" in system:
            name = "Fleet Commander Agent"
        elif "Reviewer" in system:
            name = "Reviewer Agent"
        elif "DevOps" in system:
            name = "DevOps Agent"
        elif "Mobile" in system:
            name = "Mobile Agent"
        elif "Cloud" in system:
            name = "Cloud Agent"
        return (
            f"[offline mode — no API key and no local Ollama]\n"
            f"{name} received:\n{user}\n\n"
            f"Set any of these in your environment or .env to enable full LLM "
            f"responses: OPENAI_API_KEY, DEEPSEEK_API_KEY, DASHSCOPE_API_KEY "
            f"(Qwen), GROQ_API_KEY, OPENROUTER_API_KEY, MISTRAL_API_KEY or "
            f"GITHUB_TOKEN — or install Ollama (ollama.com) and run "
            f"`ollama pull qwen3-coder` for a fully local backend. "
            f"Switch providers anytime with `set_model('provider', 'model')` "
            f"or the /model command."
        )
