from __future__ import annotations

import pytest

from invesagent_agent.clients.llm_client import (
    _extract_usage,
    _get_provider_config,
    _stable_prompt_cache_key,
)


def test_provider_registry_is_limited_to_openai_and_deepseek() -> None:
    assert _get_provider_config("openai").supports_prompt_cache_key is True
    assert _get_provider_config("deepseek").supports_prompt_cache_key is False

    with pytest.raises(ValueError):
        _get_provider_config("qwen")


def test_prompt_cache_key_uses_stable_system_messages_only() -> None:
    first = _stable_prompt_cache_key(
        [
            {"role": "system", "content": "stable instructions"},
            {"role": "user", "content": "dynamic request A"},
        ]
    )
    second = _stable_prompt_cache_key(
        [
            {"role": "system", "content": "stable instructions"},
            {"role": "user", "content": "dynamic request B"},
        ]
    )

    assert first
    assert first == second


def test_extract_usage_supports_openai_cached_tokens() -> None:
    response = {
        "usage": {
            "prompt_tokens": 1200,
            "completion_tokens": 300,
            "total_tokens": 1500,
            "prompt_tokens_details": {"cached_tokens": 1024},
        }
    }

    assert _extract_usage(response) == {
        "input_tokens": 1200,
        "output_tokens": 300,
        "total_tokens": 1500,
        "cached_tokens": 1024,
        "cache_miss_tokens": None,
        "cache_hit": True,
    }


def test_extract_usage_supports_deepseek_cache_fields() -> None:
    response = {
        "usage": {
            "prompt_tokens": 1200,
            "completion_tokens": 300,
            "total_tokens": 1500,
            "prompt_cache_hit_tokens": 900,
            "prompt_cache_miss_tokens": 300,
        }
    }

    assert _extract_usage(response) == {
        "input_tokens": 1200,
        "output_tokens": 300,
        "total_tokens": 1500,
        "cached_tokens": 900,
        "cache_miss_tokens": 300,
        "cache_hit": True,
    }
