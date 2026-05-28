from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from collections.abc import Callable
from typing import Any

from invesagent_agent.clients.llm_client import generate_json, generate_text
from invesagent_agent.clients.tool_client import ToolClient, get_tool_client
from invesagent_agent.runtime.context_builder import ContextBuilder
from invesagent_agent.runtime.memory import MemoryManager
from invesagent_agent.runtime.progress import ProgressEmitter, get_progress_emitter
from invesagent_agent.runtime.prompt_builder import DEFAULT_PROMPT_BUILDER
from invesagent_agent.runtime.trace import append_trace


LLM_JSON_CONTRACT = "Return only one valid JSON object. Do not wrap it in Markdown."


@dataclass
class AgentRuntime:
    """Execution environment for a single agent node."""

    state: dict[str, Any]
    agent_name: str
    tool_client: ToolClient | None = None
    progress: ProgressEmitter | None = None
    generate_json_fn: Callable[..., dict[str, Any]] = generate_json
    generate_text_fn: Callable[..., Any] = generate_text

    @property
    def memory(self) -> MemoryManager:
        return MemoryManager(self.state)

    @property
    def context_builder(self) -> ContextBuilder:
        return ContextBuilder(self.state)

    @property
    def warnings(self) -> list[str]:
        return list(self.state.get("warnings", []))

    def context(self, extra: dict[str, Any] | None = None) -> dict[str, Any]:
        return self.context_builder.for_agent(self.agent_name, extra=extra)

    def trace(self, event: str, payload: dict[str, Any] | None = None) -> None:
        self.state["trace"] = append_trace(
            self.state,
            event=event,
            node=self.agent_name,
            payload=payload or {},
        )

    def emit_progress(self, message: str, payload: dict[str, Any] | None = None) -> None:
        emitter = get_progress_emitter(self.progress or self.state.get("progress_emitter"))
        if emitter is not None:
            emitter.emit(node=self.agent_name, message=message, payload=payload)

    def call_tool(
        self,
        tool: str,
        arguments: dict[str, Any],
        *,
        observation: dict[str, Any] | None = None,
        default_result: Any = None,
        raise_on_error: bool = True,
    ) -> Any:
        tool_calls = list(self.state.get("tool_calls", []))
        observations = list(self.state.get("observations", []))
        warnings = self.warnings
        call = {"node": self.agent_name, "tool": tool, "arguments": arguments}
        tool_calls.append(call)
        self.state["tool_calls"] = tool_calls
        self.trace("tool_requested", {"tool": tool, "arguments": arguments})
        started = perf_counter()
        client = get_tool_client(self.tool_client or self.state.get("tool_client"))
        try:
            result = client.call_tool(tool, arguments)
        except Exception as exc:
            elapsed_ms = round((perf_counter() - started) * 1000, 2)
            warnings.append(f"{self.agent_name}: {tool} failed: {exc}")
            observations.append(
                {
                    "node": self.agent_name,
                    "tool": tool,
                    "success": False,
                    "error": str(exc),
                    "elapsed_ms": elapsed_ms,
                    **(observation or {}),
                }
            )
            self.state["warnings"] = warnings
            self.state["observations"] = observations
            self.trace("tool_failed", {"tool": tool, "error": str(exc), "elapsed_ms": elapsed_ms})
            if raise_on_error:
                raise
            return default_result

        elapsed_ms = round((perf_counter() - started) * 1000, 2)
        success = result.get("success") if isinstance(result, dict) else None
        observations.append(
            {
                "node": self.agent_name,
                "tool": tool,
                "success": success,
                "elapsed_ms": elapsed_ms,
                **(observation or {}),
            }
        )
        self.state["observations"] = observations
        self.trace(
            "tool_completed",
            {"tool": tool, "success": success, "elapsed_ms": elapsed_ms, **(observation or {})},
        )
        return result

    def call_llm_json(
        self,
        *,
        system_prompt: str,
        context: dict[str, Any],
        fallback: dict[str, Any],
        task: str = "Use the supplied context to return structured analysis.",
    ) -> dict[str, Any]:
        try:
            self.trace("llm_requested", {"format": "json"})
            result = self.generate_json_fn(
                DEFAULT_PROMPT_BUILDER.build_messages(
                    role=self.agent_name,
                    system_prompt=system_prompt,
                    task=task,
                    context=context,
                    memory=self.memory.for_agent(self.agent_name),
                    output_contract=LLM_JSON_CONTRACT,
                )
            )
            self.trace("llm_completed", {"format": "json"})
            return result
        except Exception as exc:
            warnings = self.warnings
            warnings.append(f"{self.agent_name}: LLM JSON fallback used: {exc}")
            self.state["warnings"] = warnings
            self.trace("llm_failed", {"format": "json", "error": str(exc)})
            return {**fallback, "_llm_error": str(exc)}

    def call_llm_text(
        self,
        *,
        system_prompt: str,
        context: dict[str, Any],
        fallback: str,
        task: str = "Use the supplied context to generate the final text.",
    ) -> str:
        try:
            self.trace("llm_requested", {"format": "text"})
            response = self.generate_text_fn(
                DEFAULT_PROMPT_BUILDER.build_messages(
                    role=self.agent_name,
                    system_prompt=system_prompt,
                    task=task,
                    context=context,
                    memory=self.memory.for_agent(self.agent_name),
                )
            )
            self.trace("llm_completed", {"format": "text"})
            return response.content.strip() or fallback
        except Exception as exc:
            warnings = self.warnings
            warnings.append(f"{self.agent_name}: LLM text fallback used: {exc}")
            self.state["warnings"] = warnings
            self.trace("llm_failed", {"format": "text", "error": str(exc)})
            return fallback

    def finish(self, updates: dict[str, Any]) -> dict[str, Any]:
        return {
            **self.state,
            **updates,
            "warnings": self.state.get("warnings", []),
            "trace": self.state.get("trace", []),
            "tool_calls": self.state.get("tool_calls", []),
            "observations": self.state.get("observations", []),
        }
