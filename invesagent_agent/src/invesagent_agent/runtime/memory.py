from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


_SESSION_KEYS = {
    "last_query",
    "last_task_plan",
    "last_required_agents",
    "last_symbols",
    "last_industry",
    "last_date_range",
    "last_warnings",
    "last_outputs",
    "unresolved_clarification",
}


@dataclass
class AgentMemory:
    """Structured session memory shared by chat and research workflows."""

    last_query: str = ""
    last_task_plan: dict[str, Any] = field(default_factory=dict)
    last_required_agents: list[str] = field(default_factory=list)
    last_symbols: list[str] = field(default_factory=list)
    last_industry: str | None = None
    last_date_range: dict[str, Any] = field(default_factory=dict)
    last_warnings: list[str] = field(default_factory=list)
    last_outputs: dict[str, Any] = field(default_factory=dict)
    unresolved_clarification: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_value(cls, value: Any) -> "AgentMemory":
        if isinstance(value, cls):
            return value
        if not isinstance(value, dict):
            return cls()
        source = value.get("session") if isinstance(value.get("session"), dict) else value
        return cls(
            last_query=str(source.get("last_query") or ""),
            last_task_plan=dict(source.get("last_task_plan") or {}),
            last_required_agents=[
                str(item) for item in source.get("last_required_agents", []) if item
            ],
            last_symbols=[str(item) for item in source.get("last_symbols", []) if item],
            last_industry=source.get("last_industry"),
            last_date_range=dict(source.get("last_date_range") or {}),
            last_warnings=[str(item) for item in source.get("last_warnings", []) if item],
            last_outputs=dict(source.get("last_outputs") or {}),
            unresolved_clarification=dict(source.get("unresolved_clarification") or {}),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "last_query": self.last_query,
            "last_task_plan": self.last_task_plan,
            "last_required_agents": self.last_required_agents,
            "last_symbols": self.last_symbols,
            "last_industry": self.last_industry,
            "last_date_range": self.last_date_range,
            "last_warnings": self.last_warnings,
            "last_outputs": self.last_outputs,
            "unresolved_clarification": self.unresolved_clarification,
        }

    def for_prompt(self) -> dict[str, Any]:
        return {
            "last_query": self.last_query,
            "last_task_plan": self.last_task_plan,
            "last_required_agents": self.last_required_agents,
            "last_symbols": self.last_symbols,
            "last_industry": self.last_industry,
            "last_date_range": self.last_date_range,
            "unresolved_clarification": self.unresolved_clarification,
        }


@dataclass
class MemoryManager:
    """Read and write session, task, and agent-private memory scopes."""

    state: dict[str, Any]

    def root(self) -> dict[str, Any]:
        raw = self.state.get("task_memory", {})
        if not isinstance(raw, dict):
            raw = {}

        if any(key in raw for key in ("session", "task", "agents", "long_term")):
            session = raw.get("session") if isinstance(raw.get("session"), dict) else {}
            task = raw.get("task") if isinstance(raw.get("task"), dict) else {}
            agents = raw.get("agents") if isinstance(raw.get("agents"), dict) else {}
            long_term = raw.get("long_term") if isinstance(raw.get("long_term"), str) else ""
        else:
            session = {key: raw.get(key) for key in _SESSION_KEYS if key in raw}
            task = {}
            agents = raw.get("agent_memory") if isinstance(raw.get("agent_memory"), dict) else {}
            long_term = ""

        root = {"session": session, "task": task, "agents": agents, "long_term": long_term}
        self.state["task_memory"] = root
        return root

    def session(self) -> dict[str, Any]:
        return self.root()["session"]

    def task(self) -> dict[str, Any]:
        return self.root()["task"]

    def agents(self) -> dict[str, dict[str, Any]]:
        return self.root()["agents"]

    def long_term(self) -> str:
        return str(self.root().get("long_term") or "")

    def agent_private(self, agent_name: str) -> dict[str, Any]:
        agents = self.agents()
        value = agents.get(agent_name)
        if not isinstance(value, dict):
            value = {}
            agents[agent_name] = value
        return value

    def for_agent(self, agent_name: str) -> dict[str, Any]:
        task_memory = dict(self.task())
        task_memory.update(
            {
                "task_plan": self.state.get("task_plan", task_memory.get("task_plan", {})),
                "required_agents": self.state.get(
                    "required_agents", task_memory.get("required_agents", [])
                ),
                "symbols": self.state.get("symbols", task_memory.get("symbols", [])),
                "industry": self.state.get("industry", task_memory.get("industry")),
                "date_ranges": self.state.get("date_ranges", task_memory.get("date_ranges", {})),
            }
        )
        return {
            "session": AgentMemory.from_value({"session": self.session()}).for_prompt(),
            "task": task_memory,
            "agent_private": dict(self.agent_private(agent_name)),
            "long_term": self.long_term(),
        }

    def update_session(self, **updates: Any) -> dict[str, Any]:
        session = self.session()
        session.update({key: value for key, value in updates.items() if value is not None})
        return self.root()

    def update_task(self, **updates: Any) -> dict[str, Any]:
        task = self.task()
        task.update({key: value for key, value in updates.items() if value is not None})
        return self.root()

    def update_agent_private(self, agent_name: str, **updates: Any) -> dict[str, Any]:
        agent_memory = self.agent_private(agent_name)
        agent_memory.update({key: value for key, value in updates.items() if value is not None})
        return self.root()

    def update_long_term(self, content: str) -> dict[str, Any]:
        root = self.root()
        root["long_term"] = content
        self.state["task_memory"] = root
        return root

    def capture_agent_output(self, agent_name: str, state: dict[str, Any]) -> dict[str, Any]:
        public_output = _agent_public_output(agent_name, state)
        if public_output:
            public_outputs = self.task().setdefault("public_outputs", {})
            if isinstance(public_outputs, dict):
                public_outputs[agent_name] = public_output

        self.update_task(
            task_plan=state.get("task_plan"),
            required_agents=state.get("required_agents"),
            symbols=state.get("symbols"),
            industry=state.get("industry"),
            date_ranges=state.get("date_ranges"),
            completed_agents=_append_unique(self.task().get("completed_agents", []), agent_name),
        )
        private_output = _agent_private_output(agent_name, state)
        if private_output:
            self.update_agent_private(agent_name, **private_output)
        return self.root()


def _append_unique(values: Any, value: str) -> list[str]:
    items = [str(item) for item in values if item] if isinstance(values, list) else []
    if value not in items:
        items.append(value)
    return items


def _analysis_summary(package: Any) -> dict[str, Any]:
    if not isinstance(package, dict):
        return {}
    analysis = package.get("analysis") if isinstance(package.get("analysis"), dict) else {}
    return {
        "summary": analysis.get("summary"),
        "key_findings": analysis.get("key_findings", []),
        "risks": analysis.get("risks", []),
        "data_limits": analysis.get("data_limits", []),
        "date_range": package.get("date_range"),
        "requested_date_range": package.get("requested_date_range"),
        "actual_data_range": package.get("actual_data_range"),
        "actual_data_range_by_symbol": package.get("actual_data_range_by_symbol"),
        "trading_days": package.get("trading_days"),
        "trading_days_by_symbol": package.get("trading_days_by_symbol"),
    }


def _chart_refs(charts: Any) -> list[dict[str, Any]]:
    if not isinstance(charts, list):
        return []
    refs = []
    for chart in charts:
        if not isinstance(chart, dict):
            continue
        refs.append(
            {
                "symbol": chart.get("symbol"),
                "path": chart.get("relative_path") or chart.get("path"),
                "title": chart.get("title"),
            }
        )
    return refs


def _agent_public_output(agent_name: str, state: dict[str, Any]) -> dict[str, Any]:
    if agent_name == "data_collector":
        return {
            "symbols": state.get("symbols", []),
            "industry": state.get("industry"),
            "instrument_count": len(state.get("data_package", {}).get("instruments", [])),
        }
    if agent_name == "price_volume_analyst":
        return {
            **_analysis_summary(state.get("price_volume_analysis")),
            "charts": _chart_refs(state.get("charts", [])),
        }
    if agent_name == "valuation_analyst":
        return _analysis_summary(state.get("valuation_analysis"))
    if agent_name == "fundamental_analyst":
        return _analysis_summary(state.get("fundamental_analysis"))
    if agent_name == "industry_analyst":
        return _analysis_summary(state.get("industry_analysis"))
    if agent_name == "reviewer":
        review = state.get("reflection", {})
        return {
            "status": review.get("status") if isinstance(review, dict) else None,
            "summary": review.get("summary") if isinstance(review, dict) else None,
            "review_comments": state.get("review_comments", []),
        }
    if agent_name == "investment_task_manager":
        return {
            "task_plan": state.get("task_plan", {}),
            "required_agents": state.get("required_agents", []),
        }
    if agent_name == "investment_task_reviewer":
        return {"report_review": state.get("report_review", {})}
    if agent_name == "report_writer":
        return {
            "report_type": state.get("report_context", {}).get("report_type"),
            "final_response": state.get("final_response"),
            "has_final_report": bool(state.get("final_report")),
        }
    return {}


def _agent_private_output(agent_name: str, state: dict[str, Any]) -> dict[str, Any]:
    if agent_name == "data_collector":
        cache = {}
        for item in state.get("data_package", {}).get("instruments", []):
            if isinstance(item, dict) and item.get("symbol"):
                cache[str(item.get("query") or item.get("name") or item["symbol"])] = item["symbol"]
        return {"resolved_symbol_cache": cache} if cache else {}
    if agent_name == "price_volume_analyst":
        return {
            "last_indicator_config": {
                "ma_windows": [5, 20],
                "indicators": ["bollinger", "rsi", "macd"],
            },
            "last_chart_paths": [item.get("path") for item in _chart_refs(state.get("charts", []))],
        }
    if agent_name == "report_writer":
        return {
            "last_report_type": state.get("report_context", {}).get("report_type"),
            "last_report_title": state.get("report_context", {}).get("title"),
        }
    return {}


def normalize_agent_memory(value: Any) -> dict[str, Any]:
    state = {"task_memory": value if isinstance(value, dict) else {}}
    return MemoryManager(state).root()
