from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_SKILL_PATH = PROJECT_ROOT / "skills" / "financial-report"

REPORT_PROMPTS = {
    "stock_trend_report": "stock_technical_analysis.md",
    "stock_technical_analysis": "stock_technical_analysis.md",
    "company_research_report": "company_research.md",
    "company_research": "company_research.md",
    "industry_research_report": "industry_research.md",
    "industry_research": "industry_research.md",
    "macro_research_report": "macro_research.md",
    "macro_research": "macro_research.md",
    "company_valuation_report": "company_valuation.md",
    "company_valuation": "company_valuation.md",
    "stock_investment_recommendation_report": "stock_investment_recommendation.md",
    "stock_investment_recommendation": "stock_investment_recommendation.md",
    "generic_report": "generic.md",
    "generic_research": "generic.md",
}


class FinancialReportSkill:
    """Runtime adapter for the project-local financial-report Codex skill."""

    def __init__(self, skill_path: str | Path | None = None) -> None:
        configured = skill_path or os.getenv("FINANCIAL_REPORT_SKILL_PATH")
        self.skill_path = Path(configured) if configured else DEFAULT_SKILL_PATH
        if not self.skill_path.is_absolute():
            self.skill_path = (PROJECT_ROOT / self.skill_path).resolve()

    @property
    def available(self) -> bool:
        return (self.skill_path / "SKILL.md").exists()

    def prompt_path_for(self, report_type: str | None) -> Path:
        prompt_name = REPORT_PROMPTS.get(str(report_type or "").strip(), "generic.md")
        return self.skill_path / "prompts" / prompt_name

    def load_prompt(self, report_type: str | None) -> str:
        path = self.prompt_path_for(report_type)
        if path.exists():
            return path.read_text(encoding="utf-8")
        generic = self.skill_path / "prompts" / "generic.md"
        if generic.exists():
            return generic.read_text(encoding="utf-8")
        raise FileNotFoundError(f"financial-report skill prompt not found for report_type={report_type!r}")

    def render(
        self,
        *,
        markdown: str,
        output_path: str | Path,
        output_format: str,
        title: str = "InvesAgent Report",
    ) -> Path:
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        normalized = output_format.lower().lstrip(".")
        if normalized in {"md", "markdown"}:
            output.write_text(markdown, encoding="utf-8")
            return output

        script = self.skill_path / "scripts" / "render_report.py"
        if not script.exists():
            raise FileNotFoundError(f"financial-report renderer script not found: {script}")

        with tempfile.TemporaryDirectory(prefix="invesagent-report-") as tmp:
            input_path = Path(tmp) / "report.md"
            input_path.write_text(markdown, encoding="utf-8")
            completed = subprocess.run(
                [
                    sys.executable,
                    str(script),
                    "--input",
                    str(input_path),
                    "--output",
                    str(output),
                    "--format",
                    "html" if normalized == "html" else normalized,
                    "--title",
                    title,
                ],
                text=True,
                capture_output=True,
                check=False,
            )
        if completed.returncode != 0:
            message = completed.stderr.strip() or completed.stdout.strip()
            raise RuntimeError(f"financial-report renderer failed: {message}")
        return output
