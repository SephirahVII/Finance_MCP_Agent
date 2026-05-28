---
name: financial-report
description: Generate Chinese financial research reports, including company research, industry research, macro research, stock technical analysis, company valuation analysis, and stock investment recommendation reports. Use when Codex needs to choose a financial report structure, write report prompts, create Markdown/HTML/PDF reports, or render structured report content with charts, tables, and disclosures.
---

# Financial Report

Use this skill to create financial research reports from structured analysis context, market data, tool outputs, charts, and analyst summaries. Prefer this skill when a task asks for a research report, investment memo, stock trend report, valuation report, industry report, macro report, or Markdown/HTML/PDF export.

## Workflow

1. Identify `report_type`.
2. Read the matching prompt in `prompts/`.
3. Read `references/report-structures.md` for required sections.
4. Generate a Markdown report using only provided data and clearly marking missing data.
5. Render Markdown/HTML/PDF with `scripts/render_report.py` when an artifact is requested.

## Report Types

- `company_research`: company data snapshot, event description, event commentary, earnings forecast, risks, disclaimer.
- `industry_research`: investment highlights, industry basics, index/price tracking, market review, risks.
- `macro_research`: macro summary, key indicators, policy/liquidity, asset implications, risks.
- `stock_technical_analysis`: price trend, returns, volatility, drawdown, moving averages, RSI/MACD/Bollinger, volume, charts.
- `company_valuation`: fundamentals, DCF assumptions, valuation sensitivity, comparable valuation, value judgment.
- `stock_investment_recommendation`: combines technical and value analysis into a cautious, non-binding assessment.

## Data Rules

- Use only supplied `report_context`, tool outputs, citations, and chart files.
- Do not invent financial figures, forecasts, event facts, valuation assumptions, or news.
- If required data is missing, state the limitation in the relevant section.
- Always include the analysis date range and data source notes.
- Avoid direct imperative investment advice. Use phrasing such as “偏积极/中性/偏谨慎” and include risk conditions.

## Rendering

Use:

```bash
python scripts/render_report.py --input report.md --output report.html --format html
python scripts/render_report.py --input report.md --output report.pdf --format pdf
```

The renderer supports Markdown and HTML directly. PDF requires one of these optional backends:

- `weasyprint`
- `playwright`

If no PDF backend is installed, render HTML first and report that PDF conversion requires a backend.

## Resources

- `references/report-structures.md`: detailed structures for all report types.
- `references/output-formats.md`: Markdown, HTML, PDF layout rules.
- `prompts/*.md`: report-specific writing prompts.
- `assets/report.css`: default HTML/PDF stylesheet.
- `scripts/render_report.py`: Markdown/HTML/PDF renderer.
