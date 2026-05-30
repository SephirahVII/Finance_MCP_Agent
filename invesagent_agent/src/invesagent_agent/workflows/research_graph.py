from __future__ import annotations

from langgraph.graph import END, StateGraph

from invesagent_agent.agents.data_collector import run_data_collector
from invesagent_agent.agents.fundamental_analyst import run_fundamental_analyst
from invesagent_agent.agents.industry_analyst import run_industry_analyst
from invesagent_agent.agents.investment_task_manager import (
    run_investment_task_manager,
    run_investment_task_reviewer,
)
from invesagent_agent.agents.price_volume_analyst import run_price_volume_analyst
from invesagent_agent.agents.report_writer import run_report_writer
from invesagent_agent.agents.reviewer import run_reviewer
from invesagent_agent.agents.valuation_analyst import run_valuation_analyst
from invesagent_agent.runtime.memory import MemoryManager
from invesagent_agent.runtime.trace import append_trace, build_run_report
from invesagent_agent.workflows.research_state import ResearchState


AGENT_ORDER = (
    "data_collector",
    "industry_analyst",
    "price_volume_analyst",
    "valuation_analyst",
    "fundamental_analyst",
    "reviewer",
)
MODULE_TO_AGENT = {
    "data": "data_collector",
    "industry": "industry_analyst",
    "price_volume": "price_volume_analyst",
    "valuation": "valuation_analyst",
    "fundamentals": "fundamental_analyst",
    "review": "reviewer",
    "report": "report_writer",
}


def _selected_agents(state: ResearchState) -> set[str]:
    modules = state.get("task_plan", {}).get("modules", {})
    selected = set(state.get("required_agents", []))
    if isinstance(modules, dict):
        selected.update(
            MODULE_TO_AGENT[module]
            for module, enabled in modules.items()
            if enabled and module in MODULE_TO_AGENT
        )
    elif isinstance(modules, list):
        selected.update(MODULE_TO_AGENT[module] for module in modules if module in MODULE_TO_AGENT)
    return selected


def _has_agent(state: ResearchState, name: str) -> bool:
    return name in _selected_agents(state)


def _next_agent_after(state: ResearchState, current: str | None) -> str:
    if current is None and state.get("task_plan", {}).get("action") != "execute":
        return "end"

    selected = _selected_agents(state)
    if current is None:
        remaining = AGENT_ORDER
    else:
        try:
            remaining = AGENT_ORDER[AGENT_ORDER.index(current) + 1 :]
        except ValueError:
            remaining = ()

    for agent in remaining:
        if agent in selected:
            return agent
    return "investment_task_reviewer" if "report_writer" in selected else "end"


def _route_after_manager(state: ResearchState) -> str:
    return _next_agent_after(state, None)


def _route_after_data_collector(state: ResearchState) -> str:
    return _next_agent_after(state, "data_collector")


def _route_after_industry(state: ResearchState) -> str:
    return _next_agent_after(state, "industry_analyst")


def _route_after_price(state: ResearchState) -> str:
    return _next_agent_after(state, "price_volume_analyst")


def _route_after_valuation(state: ResearchState) -> str:
    return _next_agent_after(state, "valuation_analyst")


def _route_after_fundamental(state: ResearchState) -> str:
    return _next_agent_after(state, "fundamental_analyst")


def _route_after_reviewer(state: ResearchState) -> str:
    return "investment_task_reviewer"


def _route_after_task_reviewer(state: ResearchState) -> str:
    retry_agents = state.get("report_review", {}).get("retry_agents", [])
    for agent in (
        "price_volume_analyst",
        "valuation_analyst",
        "fundamental_analyst",
        "industry_analyst",
    ):
        if agent in retry_agents:
            return agent
    if state.get("report_review", {}).get("needs_report_writer") or _has_agent(state, "report_writer"):
        return "report_writer"
    return "end"


def build_research_graph():
    """Build the LangGraph multi-agent research workflow."""
    graph = StateGraph(ResearchState)

    graph.add_node("investment_task_manager", run_investment_task_manager)
    graph.add_node("data_collector", run_data_collector)
    graph.add_node("price_volume_analyst", run_price_volume_analyst)
    graph.add_node("valuation_analyst", run_valuation_analyst)
    graph.add_node("fundamental_analyst", run_fundamental_analyst)
    graph.add_node("industry_analyst", run_industry_analyst)
    graph.add_node("reviewer", run_reviewer)
    graph.add_node("investment_task_reviewer", run_investment_task_reviewer)
    graph.add_node("report_writer", run_report_writer)

    graph.set_entry_point("investment_task_manager")
    route_targets = {
        "data_collector": "data_collector",
        "industry_analyst": "industry_analyst",
        "price_volume_analyst": "price_volume_analyst",
        "valuation_analyst": "valuation_analyst",
        "fundamental_analyst": "fundamental_analyst",
        "reviewer": "reviewer",
        "investment_task_reviewer": "investment_task_reviewer",
        "report_writer": "report_writer",
        "end": END,
    }
    graph.add_conditional_edges("investment_task_manager", _route_after_manager, route_targets)
    graph.add_conditional_edges("data_collector", _route_after_data_collector, route_targets)
    graph.add_conditional_edges("industry_analyst", _route_after_industry, route_targets)
    graph.add_conditional_edges(
        "price_volume_analyst",
        _route_after_price,
        {
            "valuation_analyst": "valuation_analyst",
            "fundamental_analyst": "fundamental_analyst",
            "reviewer": "reviewer",
            "investment_task_reviewer": "investment_task_reviewer",
            "end": END,
        },
    )
    graph.add_conditional_edges(
        "valuation_analyst",
        _route_after_valuation,
        {
            "fundamental_analyst": "fundamental_analyst",
            "reviewer": "reviewer",
            "investment_task_reviewer": "investment_task_reviewer",
            "end": END,
        },
    )
    graph.add_conditional_edges(
        "fundamental_analyst",
        _route_after_fundamental,
        {
            "reviewer": "reviewer",
            "investment_task_reviewer": "investment_task_reviewer",
            "end": END,
        },
    )
    graph.add_conditional_edges(
        "reviewer",
        _route_after_reviewer,
        {"investment_task_reviewer": "investment_task_reviewer"},
    )
    graph.add_conditional_edges(
        "investment_task_reviewer",
        _route_after_task_reviewer,
        {
            "price_volume_analyst": "price_volume_analyst",
            "valuation_analyst": "valuation_analyst",
            "fundamental_analyst": "fundamental_analyst",
            "industry_analyst": "industry_analyst",
            "report_writer": "report_writer",
            "end": END,
        },
    )
    graph.add_edge("report_writer", END)

    return graph.compile()


def run_research_workflow(
    user_query: str,
    market: str = "cn",
    asset_type: str = "stock",
    provider: str = "auto",
    industry_member_limit: int = 10,
    messages: list[dict[str, str]] | None = None,
    task_memory: dict | None = None,
    tool_client=None,
) -> ResearchState:
    """Run the compiled research workflow and return the final state."""
    workflow = build_research_graph()
    initial_state: ResearchState = {
        "user_query": user_query,
        "market": market,
        "asset_type": asset_type,
        "provider": provider,
        "industry_member_limit": industry_member_limit,
        "messages": messages or [{"role": "user", "content": user_query}],
        "task_memory": MemoryManager({"task_memory": task_memory or {}}).root(),
        "tool_client": tool_client,
        "tool_calls": [],
        "observations": [],
        "analyst_notes": {},
        "reasoning_summary": {},
        "review_round": 0,
        "trace": [],
        "warnings": [],
    }
    initial_state["trace"] = append_trace(
        initial_state,
        event="research_started",
        node="research_graph",
        payload={"user_query": user_query},
    )
    result = workflow.invoke(initial_state)
    result["trace"] = append_trace(result, event="research_finished", node="research_graph")
    result["run_report"] = build_run_report(result)
    return result
