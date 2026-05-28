from __future__ import annotations

from types import SimpleNamespace

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
        return {"success": True, "warnings": [], "message": "", "tool": name}


@pytest.fixture
def mock_tool_client():
    return MockToolClient()


@pytest.fixture(autouse=True)
def mock_llm(monkeypatch):
    import invesagent_agent.agents.base as base

    def fake_json(messages, temperature=0.1):
        del messages, temperature
        return {
            "summary": "mock summary",
            "key_findings": ["mock finding"],
            "risks": [],
            "data_limits": [],
            "confidence": "medium",
            "reasoning_summary": ["mock reasoning"],
        }

    def fake_text(messages, temperature=0.2):
        del messages, temperature
        return SimpleNamespace(content="mock text response")

    monkeypatch.setattr(base, "generate_json", fake_json)
    monkeypatch.setattr(base, "generate_text", fake_text)


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
