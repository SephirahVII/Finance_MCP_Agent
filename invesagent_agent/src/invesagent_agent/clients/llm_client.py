from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[4]


def _load_env_file(path: Path) -> None:
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip().lstrip("\ufeff"), value.strip().strip('"').strip("'"))


_load_env_file(PROJECT_ROOT / ".env")


def _getenv(name: str, default: str | None = None) -> str | None:
    return os.getenv(name) or default


@dataclass(frozen=True)
class ProviderConfig:
    name: str
    api_key_env: str
    base_url_env: str
    model_env: str
    default_base_url: str | None
    default_model: str
    supports_prompt_cache_key: bool = False


PROVIDERS: dict[str, ProviderConfig] = {
    "openai": ProviderConfig(
        name="openai",
        api_key_env="OPENAI_API_KEY",
        base_url_env="OPENAI_BASE_URL",
        model_env="OPENAI_MODEL",
        default_base_url=None,
        default_model="gpt-4.1-mini",
        supports_prompt_cache_key=True,
    ),
    "deepseek": ProviderConfig(
        name="deepseek",
        api_key_env="DEEPSEEK_API_KEY",
        base_url_env="DEEPSEEK_BASE_URL",
        model_env="DEEPSEEK_MODEL",
        default_base_url="https://api.deepseek.com",
        default_model="deepseek-chat",
    ),
}


def _get_provider_config(provider: str) -> ProviderConfig:
    config = PROVIDERS.get(provider)
    if config is None:
        supported = ", ".join(sorted(PROVIDERS))
        raise ValueError(f"Unsupported LLM_PROVIDER: {provider}. Supported providers: {supported}")
    return config


def _get_llm_api_key(config: ProviderConfig) -> str:
    key = _getenv(config.api_key_env)
    if not key:
        raise RuntimeError(
            f"API key is missing for LLM provider: {config.name}. "
            f"Set {config.api_key_env} in the project root .env."
        )
    return key


def _get_llm_model_name(config: ProviderConfig) -> str:
    return (
        _getenv(config.model_env)
        or _getenv("LLM_MODEL")
        or _getenv("MODEL_NAME")
        or config.default_model
    )


def _get_llm_base_url(config: ProviderConfig) -> str | None:
    return _getenv(config.base_url_env) or _getenv("LLM_BASE_URL") or config.default_base_url


def _truthy_env(name: str, default: str = "true") -> bool:
    value = (_getenv(name, default) or "").strip().lower()
    return value not in ("0", "false", "no", "off", "")


def _prompt_cache_enabled() -> bool:
    value = (_getenv("LLM_PROMPT_CACHE", "auto") or "").strip().lower()
    return value in ("1", "true", "yes", "on", "auto")


def _stable_prompt_cache_key(messages: list[dict[str, str]]) -> str | None:
    stable_messages = [
        message
        for message in messages
        if message.get("role") in ("system", "developer") and message.get("content")
    ]
    if not stable_messages:
        return None

    payload = json.dumps(stable_messages, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _get_attr_or_item(value: Any, name: str, default: Any = None) -> Any:
    if value is None:
        return default
    if isinstance(value, dict):
        return value.get(name, default)
    return getattr(value, name, default)


def _extract_usage(response: Any) -> dict[str, Any]:
    usage = _get_attr_or_item(response, "usage")
    if not usage:
        return {}

    prompt_details = (
        _get_attr_or_item(usage, "prompt_tokens_details")
        or _get_attr_or_item(usage, "input_tokens_details")
        or {}
    )
    openai_cached = _get_attr_or_item(prompt_details, "cached_tokens", 0) or 0
    deepseek_hit = _get_attr_or_item(usage, "prompt_cache_hit_tokens", 0) or 0
    deepseek_miss = _get_attr_or_item(usage, "prompt_cache_miss_tokens", 0) or 0
    cached_tokens = int(openai_cached or deepseek_hit or 0)

    return {
        "input_tokens": _get_attr_or_item(usage, "prompt_tokens")
        or _get_attr_or_item(usage, "input_tokens"),
        "output_tokens": _get_attr_or_item(usage, "completion_tokens")
        or _get_attr_or_item(usage, "output_tokens"),
        "total_tokens": _get_attr_or_item(usage, "total_tokens"),
        "cached_tokens": cached_tokens,
        "cache_miss_tokens": int(deepseek_miss) if deepseek_miss else None,
        "cache_hit": cached_tokens > 0,
    }


def _record_usage(payload: dict[str, Any]) -> None:
    if not _truthy_env("LLM_RECORD_USAGE", "true"):
        return

    reports_dir = PROJECT_ROOT / (_getenv("REPORTS_DIR", ".runtime/reports") or ".runtime/reports")
    reports_dir.mkdir(parents=True, exist_ok=True)
    usage_path = reports_dir / "llm_usage.jsonl"
    with usage_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")


def _extract_json_object(text: str) -> dict[str, Any]:
    try:
        value = json.loads(text)
        return value if isinstance(value, dict) else {"value": value}
    except json.JSONDecodeError:
        pass

    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.DOTALL)
    if fenced:
        return json.loads(fenced.group(1))

    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return json.loads(text[start : end + 1])

    raise json.JSONDecodeError("No JSON object found", text, 0)


@dataclass(frozen=True)
class LLMResponse:
    content: str
    model: str
    provider: str
    usage: dict[str, Any]


class LLMClient:
    """Small OpenAI-compatible LLM client for workflow agent nodes."""

    def __init__(self, provider: str | None = None, model: str | None = None) -> None:
        self.provider = (provider or _getenv("LLM_PROVIDER", "openai") or "openai").lower()
        self.config = _get_provider_config(self.provider)
        self.model = model or _get_llm_model_name(self.config)
        try:
            from openai import OpenAI
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "The 'openai' package is not installed. Install invesagent-agent dependencies "
                "to enable LLM-powered workflow nodes."
            ) from exc

        self.client = OpenAI(
            api_key=_get_llm_api_key(self.config),
            base_url=_get_llm_base_url(self.config),
        )

    def generate_text(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.2,
    ) -> LLMResponse:
        prompt_cache_key = None
        extra_body: dict[str, Any] = {}
        if self.config.supports_prompt_cache_key and _prompt_cache_enabled():
            prompt_cache_key = _stable_prompt_cache_key(messages)
            if prompt_cache_key:
                extra_body["prompt_cache_key"] = prompt_cache_key

        request_kwargs: dict[str, Any] = {}
        if extra_body:
            request_kwargs["extra_body"] = extra_body

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            **request_kwargs,
        )
        content = response.choices[0].message.content or ""
        usage = _extract_usage(response)
        usage_payload = {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "provider": self.provider,
            "model": self.model,
            "prompt_cache_key": prompt_cache_key,
            "prompt_cache_supported": self.config.supports_prompt_cache_key,
            **usage,
        }
        _record_usage(usage_payload)
        return LLMResponse(
            content=content,
            model=self.model,
            provider=self.provider,
            usage=usage_payload,
        )

    def generate_json(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.1,
    ) -> dict[str, Any]:
        json_messages = [
            *messages,
            {
                "role": "system",
                "content": "只返回一个合法 JSON object，不要使用 Markdown 包裹。",
            },
        ]
        response = self.generate_text(json_messages, temperature=temperature)
        parsed = _extract_json_object(response.content)
        parsed.setdefault(
            "_llm",
            {"provider": response.provider, "model": response.model, "usage": response.usage},
        )
        return parsed


_DEFAULT_CLIENT: LLMClient | None = None


def get_llm_client() -> LLMClient:
    global _DEFAULT_CLIENT
    if _DEFAULT_CLIENT is None:
        _DEFAULT_CLIENT = LLMClient()
    return _DEFAULT_CLIENT


def generate_text(messages: list[dict[str, str]], temperature: float = 0.2) -> LLMResponse:
    return get_llm_client().generate_text(messages, temperature=temperature)


def generate_json(messages: list[dict[str, str]], temperature: float = 0.1) -> dict[str, Any]:
    return get_llm_client().generate_json(messages, temperature=temperature)
