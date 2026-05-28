from __future__ import annotations

from typing import Any

from invesagent_agent.clients.llm_client import generate_json, generate_text
from invesagent_agent.clients.tool_client import ToolClient
from invesagent_agent.runtime.agent_runtime import AgentRuntime


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


def get_module_date_range(state: dict[str, Any], module: str) -> tuple[str, str]:
    """Return a module-specific date range with legacy top-level fallback."""
    date_ranges = state.get("date_ranges", {})
    module_range = date_ranges.get(module, {}) if isinstance(date_ranges, dict) else {}
    if not isinstance(module_range, dict):
        module_range = {}
    start_date = module_range.get("start_date") or state.get("start_date", "")
    end_date = module_range.get("end_date") or state.get("end_date", "")
    return str(start_date or ""), str(end_date or "")


def run_mcp_tool_node(
    *,
    node: str,
    tool: str,
    arguments: dict[str, Any],
    tool_calls: list[dict[str, Any]],
    observations: list[dict[str, Any]],
    warnings: list[str],
    observation: dict[str, Any] | None = None,
    default_result: Any = None,
    raise_on_error: bool = True,
    tool_client: ToolClient | None = None,
    state: dict[str, Any] | None = None,
) -> Any:
    """Call an external tool and keep standard workflow traces in one place."""
    runtime_state = state if state is not None else {}
    runtime_state["tool_calls"] = tool_calls
    runtime_state["observations"] = observations
    runtime_state["warnings"] = warnings
    runtime = AgentRuntime(runtime_state, node, tool_client=tool_client)
    result = runtime.call_tool(
        tool,
        arguments,
        observation=observation,
        default_result=default_result,
        raise_on_error=raise_on_error,
    )
    tool_calls.clear()
    tool_calls.extend(runtime_state.get("tool_calls", []))
    observations.clear()
    observations.extend(runtime_state.get("observations", []))
    warnings.clear()
    warnings.extend(runtime_state.get("warnings", []))
    return result


def run_llm_json_node(
    *,
    system_prompt: str,
    context: dict[str, Any],
    fallback: dict[str, Any],
    user_prompt: str = "Use the supplied context to return structured analysis.",
    role: str = "agent",
    memory: dict[str, Any] | None = None,
    warnings: list[str] | None = None,
) -> dict[str, Any]:
    """Run an LLM JSON node, falling back to deterministic output on failure."""
    runtime_state = {"task_memory": memory or {}, "warnings": warnings or [], "trace": []}
    runtime = AgentRuntime(
        runtime_state,
        role,
        generate_json_fn=generate_json,
        generate_text_fn=generate_text,
    )
    result = runtime.call_llm_json(
        system_prompt=system_prompt,
        context=context,
        fallback=fallback,
        task=user_prompt,
    )
    if warnings is not None:
        warnings.clear()
        warnings.extend(runtime_state.get("warnings", []))
    return result


def run_llm_text_node(
    *,
    system_prompt: str,
    context: dict[str, Any],
    fallback: str,
    user_prompt: str = "Use the supplied context to generate the final text.",
    role: str = "agent",
    memory: dict[str, Any] | None = None,
    warnings: list[str] | None = None,
) -> str:
    """Run an LLM text node, falling back to deterministic output on failure."""
    runtime_state = {"task_memory": memory or {}, "warnings": warnings or [], "trace": []}
    runtime = AgentRuntime(
        runtime_state,
        role,
        generate_json_fn=generate_json,
        generate_text_fn=generate_text,
    )
    result = runtime.call_llm_text(
        system_prompt=system_prompt,
        context=context,
        fallback=fallback,
        task=user_prompt,
    )
    if warnings is not None:
        warnings.clear()
        warnings.extend(runtime_state.get("warnings", []))
    return result
