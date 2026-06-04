from __future__ import annotations

import pytest

from invesagent_agent.agents.data_collector import run_data_collector
from invesagent_agent.agents.fundamental_analyst import run_fundamental_analyst
from invesagent_agent.agents.general_assistant import run_general_assistant
from invesagent_agent.agents.general_assistant import _heuristic_route
from invesagent_agent.agents.industry_analyst import run_industry_analyst
from invesagent_agent.agents.investment_task_manager import (
    run_investment_task_manager,
    run_investment_task_reviewer,
)
from invesagent_agent.agents.macro_policy_analyst import run_macro_policy_analyst
from invesagent_agent.agents.news_analyst import run_news_analyst
from invesagent_agent.agents.price_volume_analyst import run_price_volume_analyst
from invesagent_agent.agents.report_writer import run_report_writer
from invesagent_agent.agents.reviewer import run_reviewer
from invesagent_agent.agents.valuation_analyst import run_valuation_analyst


class MockToolClient:
    def __init__(self) -> None:
        self.calls = []

    def call_tool(self, name, arguments=None):
        arguments = arguments or {}
        self.calls.append((name, arguments))
        if name == "list_industries_tool":
            return {"success": True, "industries": ["白酒"]}
        if name == "resolve_instrument_tool":
            query = arguments.get("query", "600519.SH")
            return {"success": True, "symbol": query, "market": "cn"}
        if name == "get_industry_members_tool":
            return {
                "success": True,
                "count": 2,
                "members": [{"symbol": "600519.SH"}, {"symbol": "000858.SZ"}],
            }
        if name == "generate_ohlcv_price_chart_tool":
            return {"success": True, "relative_path": "charts/mock.png"}
        if name == "get_news_or_research_tool":
            return {
                "success": True,
                "count": 1,
                "records": [
                    {
                        "category": arguments.get("keyword", "news"),
                        "symbol": arguments.get("symbol"),
                        "date": "20240601",
                        "title": "mock news title",
                        "name": "mock source",
                        "url": "https://example.com/news",
                        "provider": arguments.get("provider", "auto"),
                    }
                ],
            }
        return {"success": True, "warnings": [], "message": "", "tool": name}


@pytest.fixture
def mock_tool_client():
    return MockToolClient()


@pytest.fixture(autouse=True)
def mock_llm(monkeypatch):
    from invesagent_agent.runtime.agent_runtime import AgentRuntime

    def fake_json(self, *, system_prompt, context, fallback, task=""):
        del self, system_prompt, context, fallback, task
        return {
            "route": "general_answer",
            "action": "execute",
            "summary": "mock summary",
            "key_findings": ["mock finding"],
            "risks": [],
            "data_limits": [],
            "confidence": "medium",
            "reasoning_summary": ["mock reasoning"],
        }

    def fake_text(self, *, system_prompt, context, fallback, task=""):
        del self, system_prompt, context, fallback, task
        return "mock text response"

    monkeypatch.setattr(AgentRuntime, "call_llm_json", fake_json)
    monkeypatch.setattr(AgentRuntime, "call_llm_text", fake_text)


def base_state(mock_tool_client):
    return {
        "user_query": "分析 600519.SH 2024-01-01 到 2024-03-31 的走势和估值",
        "market": "cn",
        "asset_type": "stock",
        "provider": "auto",
        "industry_member_limit": 3,
        "symbols": ["600519.SH"],
        "industry": "白酒",
        "start_date": "20240101",
        "end_date": "20240331",
        "date_ranges": {
            "price_volume": {"start_date": "20240101", "end_date": "20240331"},
            "valuation": {"start_date": "20240101", "end_date": "20240331"},
            "fundamentals": {"start_date": "20240101", "end_date": "20240331"},
            "industry": {"start_date": "20240101", "end_date": "20240331"},
            "news": {"start_date": "20240301", "end_date": "20240331"},
        },
        "task_plan": {"action": "execute", "modules": {"report": True}},
        "required_agents": [
            "data_collector",
            "industry_analyst",
            "price_volume_analyst",
            "valuation_analyst",
            "fundamental_analyst",
            "reviewer",
            "report_writer",
        ],
        "messages": [{"role": "user", "content": "分析 600519.SH"}],
        "task_memory": {},
        "tool_client": mock_tool_client,
        "tool_calls": [],
        "observations": [],
        "analyst_notes": {},
        "reasoning_summary": {},
        "warnings": [],
        "trace": [],
        "review_round": 0,
    }


def test_general_assistant_routes_with_mock_llm(mock_tool_client):
    state = {
        "user_query": "你好",
        "messages": [{"role": "user", "content": "你好"}],
        "task_memory": {},
        "tool_client": mock_tool_client,
        "warnings": [],
    }
    result = run_general_assistant(state)
    assert result["conversation_route"] in {"general_answer", "investment_task"}


def test_general_assistant_heuristic_routes_named_reports_to_research():
    result = _heuristic_route("\u7ed9\u6211\u6b65\u6b65\u9ad82025\u5e74\u5168\u5e74\u7684\u5206\u6790\u62a5\u544a")
    assert result["route"] == "investment_task"


def test_investment_task_manager_uses_tool_client(mock_tool_client):
    state = base_state(mock_tool_client)
    result = run_investment_task_manager(state)
    assert "task_plan" in result
    assert any(name == "list_industries_tool" for name, _ in mock_tool_client.calls)


def test_data_collector_records_tool_calls(mock_tool_client):
    result = run_data_collector(base_state(mock_tool_client))
    assert result["data_package"]["instruments"]
    assert result["tool_calls"]


def test_industry_analyst_records_analysis(mock_tool_client):
    result = run_industry_analyst(base_state(mock_tool_client))
    assert "industry_analysis" in result
    assert result["observations"]


def test_investment_task_manager_routes_macro_policy(mock_tool_client, monkeypatch):
    monkeypatch.setattr(
        "invesagent_agent.agents.investment_task_manager._try_resolve_symbol",
        lambda query, tool_client=None: [],
    )
    state = base_state(mock_tool_client)
    state["user_query"] = "\u8d22\u653f\u653f\u7b56\u5bf9\u6269\u5185\u9700\u7684\u5f71\u54cd"
    state["symbols"] = []
    state["industry"] = None
    state["task_plan"] = {}
    result = run_investment_task_manager(state)
    assert "macro_policy_analyst" in result["required_agents"]
    assert result["task_plan"]["modules"]["macro_policy"] is True


def test_investment_task_manager_routes_news(mock_tool_client):
    state = base_state(mock_tool_client)
    state["user_query"] = "600519.SH 最近有什么新闻热点"
    result = run_investment_task_manager(state)
    assert "news_analyst" in result["required_agents"]
    assert result["task_plan"]["modules"]["news"] is True


def test_macro_policy_analyst_records_rag_evidence(mock_tool_client, monkeypatch):
    class Hit:
        chunk_id = "chunk-1"
        doc_id = "doc-1"
        text = "policy evidence"
        score = 0.9
        title = "Policy Doc"
        source_type = "macro_policy"
        source_name = "source"
        jurisdiction_level = "central"
        region = "cn"
        year = 2024
        source_path = "policy.md"
        topics = ["fiscal"]
        content_categories = ["policy"]
        policy_tools = ["fiscal"]
        mentioned_industries = []
        dense_score = None
        bm25_score = 1.2
        retrieval_method = "bm25"

    def fake_retrieve(query, *, start_year, end_year, top_k):
        del query, start_year, end_year, top_k
        from invesagent_agent.agents.macro_policy_analyst import _hit_to_dict

        return [_hit_to_dict(Hit())], [], "bm25"

    monkeypatch.setattr(
        "invesagent_agent.agents.macro_policy_analyst._retrieve_policy_evidence",
        fake_retrieve,
    )
    state = base_state(mock_tool_client)
    state["user_query"] = "\u8d22\u653f\u653f\u7b56\u548c\u6269\u5185\u9700"
    state["date_ranges"]["macro_policy"] = {"start_date": "20240101", "end_date": "20241231"}
    result = run_macro_policy_analyst(state)
    assert result["macro_policy_analysis"]["raw"]["hits"][0]["chunk_id"] == "chunk-1"
    assert result["analyst_notes"]["macro_policy"]["summary"] == "mock summary"


def test_news_analyst_records_news_analysis(mock_tool_client):
    result = run_news_analyst(base_state(mock_tool_client))
    assert "news_analysis" in result
    assert result["news_analysis"]["raw"]["news_records"]
    assert result["analyst_notes"]["news"]["summary"] == "mock summary"
    assert any(name == "get_news_or_research_tool" for name, _ in mock_tool_client.calls)


def test_price_volume_analyst_records_analysis_and_chart(mock_tool_client):
    result = run_price_volume_analyst(base_state(mock_tool_client))
    assert "price_volume_analysis" in result
    assert result["charts"]


def test_valuation_analyst_records_analysis(mock_tool_client):
    result = run_valuation_analyst(base_state(mock_tool_client))
    assert "valuation_analysis" in result
    assert result["tool_calls"]


def test_fundamental_analyst_records_analysis(mock_tool_client):
    result = run_fundamental_analyst(base_state(mock_tool_client))
    assert "fundamental_analysis" in result
    assert result["tool_calls"]


def test_reviewer_records_reflection(mock_tool_client):
    result = run_reviewer(base_state(mock_tool_client))
    assert "reflection" in result
    assert "review_comments" in result


def test_investment_task_reviewer_records_report_review(mock_tool_client):
    state = base_state(mock_tool_client)
    state["price_volume_analysis"] = {"raw": {"600519.SH": {"success": True}}}
    state["valuation_analysis"] = {"raw": {"600519.SH": {"success": True}}}
    state["fundamental_analysis"] = {"raw": {"600519.SH": {"success": True}}}
    state["industry_analysis"] = {"raw": {"success": True}}
    result = run_investment_task_reviewer(state)
    assert "report_review" in result


def test_report_writer_returns_final_report(mock_tool_client):
    state = base_state(mock_tool_client)
    state["price_volume_analysis"] = {"analysis": {"summary": "price"}}
    state["valuation_analysis"] = {"analysis": {"summary": "valuation"}}
    state["fundamental_analysis"] = {"analysis": {"summary": "fundamental"}}
    state["industry_analysis"] = {"analysis": {"summary": "industry"}}
    result = run_report_writer(state)
    assert result["final_report"] == "mock text response"
