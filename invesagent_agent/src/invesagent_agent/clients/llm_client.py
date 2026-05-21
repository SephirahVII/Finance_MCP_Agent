from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


AGENT_PROJECT_ROOT = Path(__file__).resolve().parents[4]


def _load_env_file(path: Path) -> None:
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_env_file(AGENT_PROJECT_ROOT / ".env")
_load_env_file(AGENT_PROJECT_ROOT.parent / ".env")


def _getenv(name: str, default: str | None = None) -> str | None:
    return os.getenv(name) or default


def _get_llm_api_key(provider: str) -> str:
    key = {
        "openai": _getenv("OPENAI_API_KEY"),
        "deepseek": _getenv("DEEPSEEK_API_KEY"),
        "minimax": _getenv("MINIMAX_API_KEY"),
        "qwen": _getenv("QWEN_API_KEY"),
    }.get(provider)

    if key is None:
        raise ValueError(f"Unsupported LLM_PROVIDER: {provider}")
    if not key:
        raise RuntimeError(f"API key is missing for LLM provider: {provider}")
    return key


def _get_llm_model_name(provider: str) -> str:
    configured = _getenv("LLM_MODEL") or _getenv("MODEL_NAME")
    if configured:
        return configured

    defaults = {
        "openai": "gpt-4.1-mini",
        "deepseek": "deepseek-v4-flash",
        "minimax": "MiniMax-M1",
        "qwen": "qwen-plus",
    }
    return defaults.get(provider, "gpt-4.1-mini")


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


class LLMClient:
    """Small OpenAI-compatible LLM client for workflow agent nodes."""

    def __init__(self, provider: str | None = None, model: str | None = None) -> None:
        self.provider = (provider or _getenv("LLM_PROVIDER", "openai") or "openai").lower()
        self.model = model or _get_llm_model_name(self.provider)
        try:
            from openai import OpenAI
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "The 'openai' package is not installed. Install invesagent-agent dependencies "
                "to enable LLM-powered workflow nodes."
            ) from exc

        self.client = OpenAI(
            api_key=_get_llm_api_key(self.provider),
            base_url=_getenv("LLM_BASE_URL"),
        )

    def generate_text(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.2,
    ) -> LLMResponse:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
        )
        content = response.choices[0].message.content or ""
        return LLMResponse(content=content, model=self.model, provider=self.provider)

    def generate_json(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.1,
    ) -> dict[str, Any]:
        json_messages = [
            *messages,
            {
                "role": "system",
                "content": "Return only one valid JSON object. Do not wrap it in Markdown.",
            },
        ]
        response = self.generate_text(json_messages, temperature=temperature)
        parsed = _extract_json_object(response.content)
        parsed.setdefault("_llm", {"provider": response.provider, "model": response.model})
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
