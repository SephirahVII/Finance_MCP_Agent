from __future__ import annotations

import re

from langgraph.graph import END, StateGraph

from invesagent_agent.agents.general_assistant import run_general_assistant
from invesagent_agent.runtime.memory import AgentMemory, MemoryManager
from invesagent_agent.runtime.trace import append_trace, build_run_report
from invesagent_agent.workflows.chat_state import ChatState
from invesagent_agent.workflows.research_graph import run_research_workflow


_STOCK_CODE_RE = re.compile(r"^\s*\d{6}\.(?:SH|SZ|BJ|HK)\s*$", re.IGNORECASE)
_SUPPLEMENT_TERMS = (
    "A股",
    "a股",
    "港股",
    "H股",
    "h股",
    "美股",
    "股票走势",
    "走势报告",
    "公司报告",
    "完整报告",
    "基本面",
    "量价",
    "财务",
    "年报",
    "中报",
)
_RESET_TERMS = ("忽略之前", "重新开始", "换一个问题", "新问题")
_CORRECTION_PREFIXES = ("我说错了", "不是", "改成", "换成")


def _last_substantive_user_message(messages: list[dict[str, str]], current_query: str) -> str | None:
    for item in reversed(messages[:-1]):
        if item.get("role") != "user":
            continue
        content = str(item.get("content", "")).strip()
        if content and content != current_query:
            return content
    return None


def _looks_like_task_supplement(query: str) -> bool:
    text = query.strip()
    if _STOCK_CODE_RE.match(text):
        return True
    if len(text) <= 30 and any(term in text for term in _SUPPLEMENT_TERMS):
        return True
    return text.startswith(_CORRECTION_PREFIXES)


def _build_contextual_query(
    raw_query: str,
    messages: list[dict[str, str]],
    task_memory: dict,
) -> str:
    """Merge short follow-up answers with the latest unresolved research request."""
    query = raw_query.strip()
    if not query or any(term in query for term in _RESET_TERMS):
        return query

    memory = AgentMemory.from_value(task_memory)
    if memory.last_task_plan.get("action") == "clarification" and memory.last_query:
        anchor = memory.last_query.strip()
    else:
        anchor = _last_substantive_user_message(messages, query) or ""

    if not anchor or not _looks_like_task_supplement(query):
        return query
    if _STOCK_CODE_RE.match(query):
        return f"{anchor}\nFollow-up: user supplied stock code {query.upper()}."
    if query.startswith(_CORRECTION_PREFIXES):
        return f"Previous request: {anchor}\nUser correction: {query}\nUse the corrected task."
    return f"{anchor}\nFollow-up condition: {query}."


def _route_after_general_assistant(state: ChatState) -> str:
    route = state.get("conversation_route", "general_answer")
    return "investment_task" if route == "investment_task" else "general_answer"


def run_research_subgraph(state: ChatState) -> ChatState:
    """Run the research graph only after the router approves tool use."""
    normalized_query = state.get("general_decision", {}).get("normalized_query") or state.get("user_query", "")
    memory = AgentMemory.from_value(state.get("task_memory", {}))
    memory_root = MemoryManager({"task_memory": state.get("task_memory", {})}).root()
    research_state = run_research_workflow(
        user_query=normalized_query,
        market=state.get("market", "cn"),
        asset_type=state.get("asset_type", "stock"),
        provider=state.get("provider", "auto"),
        industry_member_limit=state.get("industry_member_limit", 10),
        messages=state.get("messages", []),
        task_memory=memory_root,
        tool_client=state.get("tool_client"),
    )
    memory_state = {"task_memory": research_state.get("task_memory", memory.to_dict())}
    updated_memory = MemoryManager(memory_state).update_session(
        last_query=normalized_query,
        last_task_plan=research_state.get("task_plan", {}),
        last_required_agents=research_state.get("required_agents", []),
        last_symbols=research_state.get("symbols", []),
        last_industry=research_state.get("industry"),
        last_date_range={
            "start_date": research_state.get("start_date"),
            "end_date": research_state.get("end_date"),
            "date_ranges": research_state.get("date_ranges", {}),
        },
        last_warnings=research_state.get("warnings", [])[-10:],
        last_outputs={
            "final_response": research_state.get("final_response"),
            "has_final_report": bool(research_state.get("final_report")),
        },
    )
    final_state: ChatState = {
        **state,
        "research_state": dict(research_state),
        "task_memory": updated_memory,
        "trace": [
            *state.get("trace", []),
            *research_state.get("trace", []),
        ],
        "final_response": research_state.get("final_response")
        or research_state.get("final_report")
        or research_state.get("draft_report")
        or "Investment research workflow completed, but no displayable result was generated.",
        "warnings": [
            *state.get("warnings", []),
            *research_state.get("warnings", []),
        ],
    }
    return {**final_state, "run_report": build_run_report(final_state)}


def build_chat_graph():
    """Build the outer chat graph with a general assistant before investment tools."""
    graph = StateGraph(ChatState)
    graph.add_node("general_assistant", run_general_assistant)
    graph.add_node("investment_task", run_research_subgraph)

    graph.set_entry_point("general_assistant")
    graph.add_conditional_edges(
        "general_assistant",
        _route_after_general_assistant,
        {
            "general_answer": END,
            "investment_task": "investment_task",
        },
    )
    graph.add_edge("investment_task", END)

    return graph.compile()


def run_chat_workflow(
    user_query: str,
    market: str = "cn",
    asset_type: str = "stock",
    provider: str = "auto",
    industry_member_limit: int = 10,
    messages: list[dict[str, str]] | None = None,
    task_memory: dict | None = None,
    tool_client=None,
) -> ChatState:
    """Run the chat router, which calls the research graph only when needed."""
    workflow = build_chat_graph()
    message_history = messages or [{"role": "user", "content": user_query}]
    memory = MemoryManager({"task_memory": task_memory or {}}).root()
    contextual_query = _build_contextual_query(user_query, message_history, memory)
    initial_state: ChatState = {
        "user_query": contextual_query,
        "raw_user_query": user_query,
        "market": market,
        "asset_type": asset_type,
        "provider": provider,
        "industry_member_limit": industry_member_limit,
        "messages": message_history,
        "task_memory": memory,
        "tool_client": tool_client,
        "trace": [],
        "warnings": [],
    }
    initial_state["trace"] = append_trace(
        initial_state,
        event="chat_started",
        node="chat_graph",
        payload={"raw_user_query": user_query, "contextual_query": contextual_query},
    )
    result = workflow.invoke(initial_state)
    result["trace"] = append_trace(result, event="chat_finished", node="chat_graph")
    result["run_report"] = build_run_report(result)
    return result
