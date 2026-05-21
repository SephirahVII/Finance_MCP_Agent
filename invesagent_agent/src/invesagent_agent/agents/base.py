from __future__ import annotations

import json
from typing import Any

from invesagent_agent.clients.llm_client import generate_json, generate_text


def compact_json(value: Any, max_chars: int = 12000) -> str:
    """Serialize context compactly and cap prompt size."""
    text = json.dumps(value, ensure_ascii=False, default=str, separators=(",", ":"))
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "...[truncated]"


def default_analysis(
    summary: str,
    key_findings: list[str] | None = None,
    risks: list[str] | None = None,
    data_limits: list[str] | None = None,
    confidence: str = "low",
) -> dict[str, Any]:
    return {
        "summary": summary,
        "key_findings": key_findings or [],
        "strengths": [],
        "risks": risks or [],
        "data_limits": data_limits or [],
        "confidence": confidence,
        "reasoning_summary": key_findings or [],
    }


def run_llm_json_node(
    *,
    system_prompt: str,
    context: dict[str, Any],
    fallback: dict[str, Any],
    user_prompt: str = "请基于以下 JSON 上下文输出结构化分析。",
    warnings: list[str] | None = None,
) -> dict[str, Any]:
    """Run an LLM JSON node, falling back to deterministic output on failure."""
    try:
        return generate_json(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"{user_prompt}\n\n{compact_json(context)}"},
            ]
        )
    except Exception as exc:
        if warnings is not None:
            warnings.append(f"LLM analysis fallback used: {exc}")
        return {**fallback, "_llm_error": str(exc)}


def run_llm_text_node(
    *,
    system_prompt: str,
    context: dict[str, Any],
    fallback: str,
    user_prompt: str = "请基于以下 JSON 上下文生成最终文本。",
    warnings: list[str] | None = None,
) -> str:
    """Run an LLM text node, falling back to deterministic output on failure."""
    try:
        response = generate_text(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"{user_prompt}\n\n{compact_json(context)}"},
            ]
        )
        return response.content.strip() or fallback
    except Exception as exc:
        if warnings is not None:
            warnings.append(f"LLM text fallback used: {exc}")
        return fallback
