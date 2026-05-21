from __future__ import annotations

from langgraph.graph import END, StateGraph

from invesagent_agent.agents.data_collector import run_data_collector
from invesagent_agent.agents.fundamental_analyst import run_fundamental_analyst
from invesagent_agent.agents.industry_analyst import run_industry_analyst
from invesagent_agent.agents.price_volume_analyst import run_price_volume_analyst
from invesagent_agent.agents.report_writer import run_report_writer
from invesagent_agent.agents.reviewer import run_reviewer
from invesagent_agent.agents.task_planner import run_task_planner
from invesagent_agent.workflows.research_state import ResearchState


def build_research_graph():
    """Build the LangGraph multi-agent research workflow."""
    graph = StateGraph(ResearchState)

    graph.add_node("task_planner", run_task_planner)
    graph.add_node("data_collector", run_data_collector)
    graph.add_node("price_volume_analyst", run_price_volume_analyst)
    graph.add_node("fundamental_analyst", run_fundamental_analyst)
    graph.add_node("industry_analyst", run_industry_analyst)
    graph.add_node("reviewer", run_reviewer)
    graph.add_node("report_writer", run_report_writer)

    graph.set_entry_point("task_planner")
    graph.add_edge("task_planner", "data_collector")
    graph.add_edge("data_collector", "industry_analyst")
    graph.add_edge("industry_analyst", "price_volume_analyst")
    graph.add_edge("price_volume_analyst", "fundamental_analyst")
    graph.add_edge("fundamental_analyst", "reviewer")
    graph.add_edge("reviewer", "report_writer")
    graph.add_edge("report_writer", END)

    return graph.compile()


def run_research_workflow(
    user_query: str,
    market: str = "cn",
    asset_type: str = "stock",
    provider: str = "auto",
    industry_member_limit: int = 10,
) -> ResearchState:
    """Run the compiled research workflow and return the final state."""
    workflow = build_research_graph()
    initial_state: ResearchState = {
        "user_query": user_query,
        "market": market,
        "asset_type": asset_type,
        "provider": provider,
        "industry_member_limit": industry_member_limit,
        "tool_calls": [],
        "observations": [],
        "analyst_notes": {},
        "reasoning_summary": {},
        "warnings": [],
    }
    return workflow.invoke(initial_state)
