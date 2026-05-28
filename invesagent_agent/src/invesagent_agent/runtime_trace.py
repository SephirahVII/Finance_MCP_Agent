from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def append_trace(
    state: dict[str, Any],
    *,
    event: str,
    node: str,
    payload: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    trace = list(state.get("trace", []))
    trace.append(
        {
            "created_at": now_iso(),
            "event": event,
            "node": node,
            "payload": payload or {},
        }
    )
    return trace


def build_run_report(state: dict[str, Any]) -> dict[str, Any]:
    return {
        "user_query": state.get("user_query"),
        "task_plan": state.get("task_plan", {}),
        "required_agents": state.get("required_agents", []),
        "tool_calls": state.get("tool_calls", []),
        "observations": state.get("observations", []),
        "warnings": state.get("warnings", []),
        "trace": state.get("trace", []),
        "final_response": state.get("final_response") or state.get("final_report"),
    }
