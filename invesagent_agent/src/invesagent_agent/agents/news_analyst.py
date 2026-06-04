from __future__ import annotations

from typing import Any

from invesagent_agent.agents.base import default_analysis, get_module_date_range
from invesagent_agent.prompts.news_analyst import NEWS_ANALYST_PROMPT
from invesagent_agent.runtime.agent_runtime import AgentRuntime
from invesagent_agent.workflows.research_state import ResearchState


def _records(result: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(result, dict):
        return []
    records = result.get("records", [])
    return records if isinstance(records, list) else []


def _record_key(record: dict[str, Any]) -> tuple[str, str, str]:
    return (
        str(record.get("date") or ""),
        str(record.get("title") or ""),
        str(record.get("url") or ""),
    )


def _dedupe_records(records: list[dict[str, Any]], *, limit: int) -> list[dict[str, Any]]:
    seen: set[tuple[str, str, str]] = set()
    deduped: list[dict[str, Any]] = []
    for record in records:
        key = _record_key(record)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(record)
    deduped.sort(key=lambda item: str(item.get("date") or ""), reverse=True)
    return deduped[:limit]


def _representative_symbols(state: ResearchState) -> list[str]:
    symbols = [symbol for symbol in state.get("symbols", []) if symbol]
    industry_members = state.get("data_package", {}).get("industry_members") or {}
    members = industry_members.get("members", []) if isinstance(industry_members, dict) else []
    if isinstance(members, list):
        symbols.extend(member.get("symbol") for member in members[:5] if isinstance(member, dict) and member.get("symbol"))
    return list(dict.fromkeys(str(symbol) for symbol in symbols if symbol))[:8]


def _fetch_news_package(
    runtime: AgentRuntime,
    *,
    symbol: str,
    market: str,
    provider: str,
    start_date: str,
    end_date: str,
    news_limit: int,
    research_limit: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    status: list[dict[str, Any]] = []
    news = runtime.call_tool(
        "get_news_or_research_tool",
        {
            "symbol": symbol,
            "market": market,
            "provider": provider,
            "keyword": "news",
            "start_date": start_date,
            "end_date": end_date,
            "limit": news_limit,
        },
        observation={"symbol": symbol, "category": "news"},
        default_result={"success": False, "records": []},
        raise_on_error=False,
    )
    status.append(
        {
            "symbol": symbol,
            "category": "news",
            "success": bool(news.get("success")) if isinstance(news, dict) else False,
            "count": len(_records(news)),
            "message": news.get("message") if isinstance(news, dict) else None,
            "error_type": news.get("error_type") if isinstance(news, dict) else None,
        }
    )
    research = runtime.call_tool(
        "get_news_or_research_tool",
        {
            "symbol": symbol,
            "market": market,
            "provider": provider,
            "keyword": "research",
            "start_date": start_date,
            "end_date": end_date,
            "limit": research_limit,
        },
        observation={"symbol": symbol, "category": "research_reports"},
        default_result={"success": False, "records": []},
        raise_on_error=False,
    )
    status.append(
        {
            "symbol": symbol,
            "category": "research_reports",
            "success": bool(research.get("success")) if isinstance(research, dict) else False,
            "count": len(_records(research)),
            "message": research.get("message") if isinstance(research, dict) else None,
            "error_type": research.get("error_type") if isinstance(research, dict) else None,
        }
    )
    return _records(news), _records(research), status


def run_news_analyst(state: ResearchState) -> ResearchState:
    """Fetch and interpret runtime news/research metadata without changing other agents."""
    runtime = AgentRuntime(state, "news_analyst")
    market = state.get("market", "cn")
    provider = state.get("provider", "auto")
    start_date, end_date = get_module_date_range(state, "news")
    symbols = _representative_symbols(state)
    news_limit = int(state.get("news_limit", 20) or 20)
    research_limit = int(state.get("research_limit", 10) or 10)

    if not symbols:
        fallback = default_analysis(
            summary="新闻分析已跳过：未识别到可用于新闻检索的股票代码或行业代表公司。",
            data_limits=["缺少 symbol，无法调用个股新闻/研报工具。"],
            confidence="low",
        )
        return runtime.finish(
            {
                "news_analysis": {
                    "skipped": True,
                    "raw": {
                        "targets": {
                            "symbols": [],
                            "industry": state.get("industry"),
                            "market": market,
                            "provider": provider,
                        },
                        "date_range": {"start_date": start_date, "end_date": end_date},
                        "news_records": [],
                        "research_records": [],
                        "tool_status": [],
                    },
                    "analysis": fallback,
                },
                "analyst_notes": {**state.get("analyst_notes", {}), "news": fallback},
                "reasoning_summary": {
                    **state.get("reasoning_summary", {}),
                    "news": fallback.get("reasoning_summary", []),
                },
            }
        )

    all_news: list[dict[str, Any]] = []
    all_research: list[dict[str, Any]] = []
    tool_status: list[dict[str, Any]] = []
    for symbol in symbols:
        news_records, research_records, status = _fetch_news_package(
            runtime,
            symbol=symbol,
            market=market,
            provider=provider,
            start_date=start_date,
            end_date=end_date,
            news_limit=news_limit,
            research_limit=research_limit,
        )
        all_news.extend(news_records)
        all_research.extend(research_records)
        tool_status.extend(status)

    news_records = _dedupe_records(all_news, limit=news_limit * max(len(symbols), 1))
    research_records = _dedupe_records(all_research, limit=research_limit * max(len(symbols), 1))
    raw = {
        "query": state.get("user_query", ""),
        "date_range": {"start_date": start_date, "end_date": end_date},
        "targets": {
            "symbols": symbols,
            "industry": state.get("industry"),
            "market": market,
            "provider": provider,
        },
        "news_records": news_records,
        "research_records": research_records,
        "tool_status": tool_status,
    }
    data_limits = []
    if not news_records:
        data_limits.append("未获取到新闻记录。")
    if not research_records:
        data_limits.append("未获取到研报记录。")
    failed = [item for item in tool_status if not item.get("success")]
    if failed:
        data_limits.append("部分新闻/研报工具调用失败或返回空数据。")

    fallback = default_analysis(
        summary=f"新闻工具返回 {len(news_records)} 条新闻和 {len(research_records)} 条研报记录。",
        key_findings=[
            f"新闻样本数量：{len(news_records)}。",
            f"研报样本数量：{len(research_records)}。",
        ],
        data_limits=data_limits,
        confidence="medium" if news_records or research_records else "low",
    )
    fallback.update(
        {
            "key_events": [],
            "hot_topics": [],
            "company_implications": [],
            "industry_implications": [],
            "risk_alerts": [],
            "citations": [
                {
                    "title": item.get("title"),
                    "date": item.get("date"),
                    "source": item.get("name") or item.get("provider"),
                    "url": item.get("url"),
                }
                for item in [*news_records, *research_records][:8]
                if item.get("title")
            ],
        }
    )

    analysis = runtime.call_llm_json(
        system_prompt=NEWS_ANALYST_PROMPT,
        context=runtime.context({"raw": raw}),
        fallback=fallback,
    )
    if data_limits:
        analysis["data_limits"] = list(dict.fromkeys([*(analysis.get("data_limits") or []), *data_limits]))

    final_response = analysis.get("summary") or fallback["summary"]
    findings = analysis.get("key_findings") or analysis.get("company_implications") or []
    if findings:
        final_response = "\n".join([final_response, *[f"- {item}" for item in findings[:5]]])

    return runtime.finish(
        {
            "news_analysis": {
                "raw": raw,
                "analysis": analysis,
                "date_range": raw["date_range"],
            },
            "analyst_notes": {
                **state.get("analyst_notes", {}),
                "news": analysis,
            },
            "reasoning_summary": {
                **state.get("reasoning_summary", {}),
                "news": analysis.get("reasoning_summary", []),
            },
            "final_response": final_response,
            "final_report": final_response,
        }
    )
