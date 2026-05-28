from __future__ import annotations

import base64
import html
import mimetypes
import re
import shutil
from pathlib import Path
from typing import Any

from invesagent_agent.reports import FinancialReportSkill


def _chart_path(chart: dict[str, Any]) -> Path | None:
    raw_path = chart.get("path") or chart.get("relative_path")
    if not raw_path:
        return None

    path = Path(str(raw_path))
    if path.is_absolute() and path.exists():
        return path
    if path.exists():
        return path.resolve()

    for base in (Path.cwd(), Path.cwd() / "invesagent_mcp"):
        candidate = base / path
        if candidate.exists():
            return candidate.resolve()
    return None


def _collect_charts(report_context: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(report_context, dict):
        return []
    charts = report_context.get("charts", [])
    if isinstance(charts, list):
        return [chart for chart in charts if isinstance(chart, dict)]

    price_package = report_context.get("price_volume_analysis", {})
    raw_charts = price_package.get("raw", {}).get("charts", []) if isinstance(price_package, dict) else []
    return [chart for chart in raw_charts if isinstance(chart, dict)]


def _chart_caption(chart: dict[str, Any], index: int) -> str:
    symbol = chart.get("symbol")
    chart_type = chart.get("chart_type")
    if symbol and chart_type:
        return f"{symbol} {chart_type} chart"
    if symbol:
        return f"{symbol} chart"
    return f"Chart {index}"


def _append_markdown_images(
    report: str,
    charts: list[dict[str, Any]],
    assets_dir: Path,
) -> str:
    image_lines: list[str] = []
    for index, chart in enumerate(charts, start=1):
        source = _chart_path(chart)
        if source is None:
            continue
        assets_dir.mkdir(parents=True, exist_ok=True)
        target = assets_dir / source.name
        if source.resolve() != target.resolve():
            shutil.copy2(source, target)
        relative = target.relative_to(assets_dir.parent).as_posix()
        image_lines.extend(["", f"![{_chart_caption(chart, index)}]({relative})"])

    if not image_lines:
        return report
    return "\n".join([report.rstrip(), "", "## 图表", *image_lines, ""])


def _image_data_uri(path: Path) -> str | None:
    mime_type = mimetypes.guess_type(path.name)[0] or "image/png"
    try:
        data = base64.b64encode(path.read_bytes()).decode("ascii")
    except OSError:
        return None
    return f"data:{mime_type};base64,{data}"


def _render_inline_markdown(text: str) -> str:
    escaped = html.escape(text)
    escaped = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escaped)
    escaped = re.sub(r"`(.+?)`", r"<code>\1</code>", escaped)
    return escaped


def _markdown_to_html_body(report: str) -> str:
    lines = report.splitlines()
    output: list[str] = []
    in_list = False
    in_code = False
    code_lines: list[str] = []

    def close_list() -> None:
        nonlocal in_list
        if in_list:
            output.append("</ul>")
            in_list = False

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("```"):
            if in_code:
                output.append(f"<pre><code>{html.escape(chr(10).join(code_lines))}</code></pre>")
                code_lines = []
                in_code = False
            else:
                close_list()
                in_code = True
            continue
        if in_code:
            code_lines.append(line)
            continue

        if not stripped:
            close_list()
            continue
        if stripped.startswith("#"):
            close_list()
            level = min(len(stripped) - len(stripped.lstrip("#")), 6)
            content = stripped[level:].strip()
            output.append(f"<h{level}>{_render_inline_markdown(content)}</h{level}>")
            continue
        if stripped.startswith("- "):
            if not in_list:
                output.append("<ul>")
                in_list = True
            output.append(f"<li>{_render_inline_markdown(stripped[2:].strip())}</li>")
            continue
        close_list()
        output.append(f"<p>{_render_inline_markdown(stripped)}</p>")

    close_list()
    if in_code:
        output.append(f"<pre><code>{html.escape(chr(10).join(code_lines))}</code></pre>")
    return "\n".join(output)


def _append_html_images(body: str, charts: list[dict[str, Any]]) -> str:
    figures: list[str] = []
    for index, chart in enumerate(charts, start=1):
        source = _chart_path(chart)
        if source is None:
            continue
        data_uri = _image_data_uri(source)
        if not data_uri:
            continue
        caption = html.escape(_chart_caption(chart, index))
        figures.append(
            f'<figure><img src="{data_uri}" alt="{caption}"><figcaption>{caption}</figcaption></figure>'
        )
    if not figures:
        return body
    return "\n".join([body, "<h2>图表</h2>", *figures])


def _html_document(title: str, body: str) -> str:
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <style>
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Microsoft YaHei", sans-serif;
      line-height: 1.68;
      color: #1f2933;
      max-width: 980px;
      margin: 40px auto;
      padding: 0 28px 48px;
      background: #ffffff;
    }}
    h1, h2, h3 {{ color: #111827; line-height: 1.25; margin-top: 1.5em; }}
    h1 {{ border-bottom: 2px solid #d7dee8; padding-bottom: 12px; }}
    p, li {{ font-size: 15px; }}
    code {{ background: #f3f4f6; padding: 1px 5px; border-radius: 4px; }}
    pre {{ background: #f6f8fa; padding: 14px; overflow: auto; border-radius: 6px; }}
    figure {{ margin: 28px 0; }}
    img {{ display: block; max-width: 100%; height: auto; border: 1px solid #d7dee8; }}
    figcaption {{ color: #64748b; font-size: 13px; margin-top: 8px; }}
  </style>
</head>
<body>
{body}
</body>
</html>
"""


def export_report(
    *,
    report: str,
    output_path: str | Path,
    output_format: str,
    report_context: dict[str, Any] | None = None,
    title: str = "InvesAgent Report",
) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    charts = _collect_charts(report_context)
    normalized_format = output_format.lower().lstrip(".")

    if normalized_format in {"md", "markdown"}:
        assets_dir = path.with_name(f"{path.stem}_assets")
        content = _append_markdown_images(report, charts, assets_dir)
        path.write_text(content, encoding="utf-8")
        return path

    if normalized_format in {"html", "pdf"}:
        assets_dir = path.with_name(f"{path.stem}_assets")
        content = _append_markdown_images(report, charts, assets_dir)
        try:
            return FinancialReportSkill().render(
                markdown=content,
                output_path=path,
                output_format=normalized_format,
                title=title,
            )
        except Exception:
            if normalized_format == "pdf":
                raise
        body = _markdown_to_html_body(content)
        body = _append_html_images(body, charts)
        path.write_text(_html_document(title, body), encoding="utf-8")
        return path

    raise ValueError(f"Unsupported report export format: {output_format}")
