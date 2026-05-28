from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class ContextBuilder:
    """Build compact, agent-specific context from workflow state."""

    state: dict[str, Any]

    def common(self) -> dict[str, Any]:
        return {
            "user_query": self.state.get("user_query", ""),
            "task_plan": self.state.get("task_plan", {}),
            "target": {
                "symbols": self.state.get("symbols", []),
                "industry": self.state.get("industry"),
                "market": self.state.get("market", "cn"),
                "asset_type": self.state.get("asset_type", "stock"),
            },
            "date_ranges": self.state.get("date_ranges", {}),
            "user_date_range": self.state.get("user_date_range", {}),
            "warnings": self.state.get("warnings", [])[-10:],
        }

    def for_agent(self, agent_name: str, extra: dict[str, Any] | None = None) -> dict[str, Any]:
        context = self.common()
        if agent_name == "price_volume_analyst":
            context.update(
                {
                    "data_package": self.state.get("data_package", {}),
                    "charts": self.state.get("charts", []),
                }
            )
        elif agent_name == "reviewer":
            context.update(
                {
                    "observations": self.state.get("observations", []),
                    "analyst_notes": self.state.get("analyst_notes", {}),
                    "price_volume_analysis": self.state.get("price_volume_analysis", {}),
                    "fundamental_analysis": self.state.get("fundamental_analysis", {}),
                    "industry_analysis": self.state.get("industry_analysis", {}),
                    "valuation_analysis": self.state.get("valuation_analysis", {}),
                }
            )
        elif agent_name == "report_writer":
            context.update(
                {
                    "analyst_notes": self.state.get("analyst_notes", {}),
                    "price_volume_analysis": self.state.get("price_volume_analysis", {}),
                    "fundamental_analysis": self.state.get("fundamental_analysis", {}),
                    "industry_analysis": self.state.get("industry_analysis", {}),
                    "valuation_analysis": self.state.get("valuation_analysis", {}),
                    "charts": self.state.get("charts", []),
                }
            )
        if extra:
            context.update(extra)
        return context

