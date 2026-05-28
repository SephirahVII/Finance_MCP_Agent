from __future__ import annotations

from time import perf_counter
from typing import Any

from invesagent_agent.clients.llm_client import generate_json, generate_text
from invesagent_agent.clients.tool_client import ToolClient, get_tool_client
from invesagent_agent.prompt_builder import DEFAULT_PROMPT_BUILDER
from invesagent_agent.runtime_trace import append_trace


LLM_JSON_CONTRACT = "Return only one valid JSON object. Do not wrap it in Markdown."


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


def _state_tool_client(state: dict[str, Any] | None, tool_client: ToolClient | None) -> ToolClient:
    if tool_client is not None:
        return get_tool_client(tool_client)
    return get_tool_client((state or {}).get("tool_client"))


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
    call = {"node": node, "tool": tool, "arguments": arguments}
    tool_calls.append(call)
    started = perf_counter()
    client = _state_tool_client(state, tool_client)
    if state is not None:
        state["trace"] = append_trace(
            state,
            event="tool_requested",
            node=node,
            payload={"tool": tool, "arguments": arguments},
        )
    try:
        result = client.call_tool(tool, arguments)
    except Exception as exc:
        elapsed_ms = round((perf_counter() - started) * 1000, 2)
        warnings.append(f"{node}: {tool} failed: {exc}")
        observations.append(
            {
                "node": node,
                "tool": tool,
                "success": False,
                "error": str(exc),
                "elapsed_ms": elapsed_ms,
                **(observation or {}),
            }
        )
        if state is not None:
            state["trace"] = append_trace(
                state,
                event="tool_failed",
                node=node,
                payload={"tool": tool, "error": str(exc), "elapsed_ms": elapsed_ms},
            )
        if raise_on_error:
            raise
        return default_result

    elapsed_ms = round((perf_counter() - started) * 1000, 2)
    success = result.get("success") if isinstance(result, dict) else None
    observations.append(
        {
            "node": node,
            "tool": tool,
            "success": success,
            "elapsed_ms": elapsed_ms,
            **(observation or {}),
        }
    )
    if state is not None:
        state["trace"] = append_trace(
            state,
            event="tool_completed",
            node=node,
            payload={
                "tool": tool,
                "success": success,
                "elapsed_ms": elapsed_ms,
                **(observation or {}),
            },
        )
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
    try:
        return generate_json(
            DEFAULT_PROMPT_BUILDER.build_messages(
                role=role,
                system_prompt=system_prompt,
                task=user_prompt,
                context=context,
                memory=memory,
                output_contract=LLM_JSON_CONTRACT,
            )
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
    user_prompt: str = "Use the supplied context to generate the final text.",
    role: str = "agent",
    memory: dict[str, Any] | None = None,
    warnings: list[str] | None = None,
) -> str:
    """Run an LLM text node, falling back to deterministic output on failure."""
    try:
        response = generate_text(
            DEFAULT_PROMPT_BUILDER.build_messages(
                role=role,
                system_prompt=system_prompt,
                task=user_prompt,
                context=context,
                memory=memory,
            )
        )
        return response.content.strip() or fallback
    except Exception as exc:
        if warnings is not None:
            warnings.append(f"LLM text fallback used: {exc}")
        return fallback
