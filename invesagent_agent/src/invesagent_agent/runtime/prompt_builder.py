from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from invesagent_agent.runtime.memory import AgentMemory


def compact_json(value: Any, max_chars: int = 12000) -> str:
    """Serialize context compactly and cap prompt size."""
    text = json.dumps(value, ensure_ascii=False, default=str, separators=(",", ":"))
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "...[truncated]"


@dataclass(frozen=True)
class PromptBuilder:
    """Build consistent messages for all LLM-backed agent nodes."""

    max_context_chars: int = 12000

    def build_messages(
        self,
        *,
        role: str,
        system_prompt: str,
        task: str,
        context: dict[str, Any],
        memory: dict[str, Any] | AgentMemory | None = None,
        output_contract: str | None = None,
    ) -> list[dict[str, str]]:
        if isinstance(memory, dict) and any(key in memory for key in ("session", "task", "agent")):
            memory_value = memory
        else:
            memory_value = AgentMemory.from_value(memory).for_prompt() if memory is not None else {}
        envelope = {
            "agent_role": role,
            "task": task,
            "memory": memory_value,
            "context": context,
        }
        if output_contract:
            envelope["output_contract"] = output_contract
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": compact_json(envelope, self.max_context_chars)},
        ]


DEFAULT_PROMPT_BUILDER = PromptBuilder()

