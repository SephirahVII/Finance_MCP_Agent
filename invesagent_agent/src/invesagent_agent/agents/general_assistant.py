from __future__ import annotations

import re
from typing import Any

from invesagent_agent.prompts.general_assistant import GENERAL_ASSISTANT_PROMPT
from invesagent_agent.runtime.agent_runtime import AgentRuntime
from invesagent_agent.workflows.chat_state import ChatState


_TS_CODE_RE = re.compile(r"\b\d{6}\.(?:SH|SZ|BJ)\b", re.IGNORECASE)
_DATE_RE = re.compile(r"\d{4}[-/]?\d{2}[-/]?\d{2}|最近[一二三四五六七八九十\d]+年|过去[一二三四五六七八九十\d]+年")
_INVESTMENT_TERMS = {
    "股票",
    "公司",
    "行业",
    "指数",
    "基金",
    "ETF",
    "港股",
    "美股",
    "数字货币",
    "估值",
    "基本面",
    "财务",
    "营收",
    "利润",
    "现金流",
    "ROE",
    "PE",
    "PB",
    "PS",
    "DCF",
    "股息率",
    "量价",
    "走势",
    "回撤",
    "波动",
    "图表",
    "研报",
}
_RESEARCH_VERBS = {
    "分析",
    "研究",
    "比较",
    "对比",
    "生成报告",
    "报告",
    "图表",
    "获取",
    "查询",
    "走势",
    "表现",
}
_CONCEPT_PATTERNS = (
    "是什么",
    "什么意思",
    "含义",
    "如何理解",
    "怎么理解",
    "解释一下",
)


_MACRO_POLICY_TERMS = {
    "macro",
    "policy",
    "宏观",
    "政策",
    "财政",
    "货币",
    "政府",
    "地方政府",
    "政府工作报告",
    "经济政策",
    "产业政策",
    "扩大内需",
    "新能源",
    "补贴",
    "专项资金",
}


def _contains_any(text: str, terms: set[str]) -> bool:
    lower = text.lower()
    return any(term.lower() in lower for term in terms)


def _heuristic_route(query: str) -> dict[str, Any]:
    text = query.strip()
    if not text:
        return {
            "route": "general_answer",
            "intent": "empty_or_greeting",
            "needs_investment_workflow": False,
            "confidence": 0.9,
            "reason": "用户没有提出明确任务。",
            "response": "我在。你可以问我项目设计、金融概念，或给出明确标的和时间让我进入投资研究流程。",
            "normalized_query": text,
        }

    has_investment_term = _contains_any(text, _INVESTMENT_TERMS)
    has_research_verb = _contains_any(text, _RESEARCH_VERBS)
    has_macro_policy_term = _contains_any(text, _MACRO_POLICY_TERMS)
    asks_concept = any(pattern in text for pattern in _CONCEPT_PATTERNS)
    has_code = bool(_TS_CODE_RE.search(text))
    has_date = bool(_DATE_RE.search(text))
    looks_like_named_research = has_research_verb and (has_date or "报告" in text or "研报" in text)

    if asks_concept and has_investment_term and not has_research_verb:
        return {
            "route": "general_answer",
            "intent": "finance_concept_explanation",
            "needs_investment_workflow": False,
            "confidence": 0.86,
            "reason": "用户在询问金融概念，不需要真实行情或财务数据。",
            "response": None,
            "normalized_query": text,
        }

    if has_macro_policy_term:
        return {
            "route": "investment_task",
            "intent": "macro_policy_research_task",
            "needs_investment_workflow": True,
            "confidence": 0.86,
            "reason": "用户提出宏观、地方政府或产业政策相关问题，应进入宏观政策 RAG 研究流程。",
            "response": None,
            "normalized_query": text,
        }

    if has_investment_term and (has_research_verb or has_code or has_date):
        return {
            "route": "investment_task",
            "intent": "investment_research_or_data_task",
            "needs_investment_workflow": True,
            "confidence": 0.82,
            "reason": "用户提出了投资研究或数据分析相关需求，应交给 Investment Task Manager。",
            "response": None,
            "normalized_query": text,
        }

    if looks_like_named_research:
        return {
            "route": "investment_task",
            "intent": "investment_research_or_data_task",
            "needs_investment_workflow": True,
            "confidence": 0.76,
            "reason": "用户提出了带时间范围或报告要求的分析任务，可能是公司或标的研究任务。",
            "response": None,
            "normalized_query": text,
        }

    return {
        "route": "general_answer",
        "intent": "general_conversation",
        "needs_investment_workflow": False,
        "confidence": 0.7,
        "reason": "最新输入未表达明确投资研究任务。",
        "response": None,
        "normalized_query": text,
    }


def run_general_assistant(state: ChatState) -> ChatState:
    """Route and answer general turns before any investment workflow is started."""
    runtime = AgentRuntime(state, "general_assistant")
    query = state.get("user_query", "")
    fallback = _heuristic_route(query)
    decision = runtime.call_llm_json(
        system_prompt=GENERAL_ASSISTANT_PROMPT,
        context={
            "latest_user_input": query,
            "recent_messages_for_context_only": state.get("messages", [])[-6:],
            "heuristic_route": fallback,
        },
        fallback=fallback,
        task="请只根据 latest_user_input 判断本轮是否进入投资研究系统。",
    )

    route = decision.get("route") or fallback["route"]
    if route not in {"general_answer", "investment_task"}:
        route = fallback["route"]
    if fallback.get("intent") == "macro_policy_research_task":
        route = "investment_task"

    if route == "investment_task":
        return runtime.finish(
            {
                "general_decision": decision,
                "conversation_route": "investment_task",
            }
        )

    response = decision.get("response")
    if not response:
        response = runtime.call_llm_text(
            system_prompt=(
                "你是 InvesAgent 的 General Assistant。请用中文自然回答。"
                "如果是金融概念解释，要清楚、简洁，不要调用或编造实时数据。"
            ),
            context={
                "latest_user_input": query,
                "decision": decision,
                "recent_messages": state.get("messages", [])[-6:],
            },
            fallback="我理解了。这个问题不需要调用金融数据工具，我可以直接和你讨论。",
        )

    return runtime.finish(
        {
            "general_decision": decision,
            "conversation_route": "general_answer",
            "final_response": response,
        }
    )
