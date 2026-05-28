from __future__ import annotations

import argparse
import html
import re
import subprocess
import sys
from pathlib import Path


def _inline_markdown(text: str) -> str:
    escaped = html.escape(text)
    escaped = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escaped)
    escaped = re.sub(r"`(.+?)`", r"<code>\1</code>", escaped)
    return escaped


def markdown_to_html_body(markdown: str) -> str:
    lines = markdown.splitlines()
    out: list[str] = []
    in_ul = False
    in_code = False
    code_lines: list[str] = []
    in_table = False
    table_rows: list[list[str]] = []

    def flush_ul() -> None:
        nonlocal in_ul
        if in_ul:
            out.append("</ul>")
            in_ul = False

    def flush_code() -> None:
        nonlocal in_code, code_lines
        if in_code:
            out.append(f"<pre><code>{html.escape(chr(10).join(code_lines))}</code></pre>")
            in_code = False
            code_lines = []

    def flush_table() -> None:
        nonlocal in_table, table_rows
        if not in_table:
            return
        out.append("<table>")
        for idx, row in enumerate(table_rows):
            tag = "th" if idx == 0 else "td"
            cells = "".join(f"<{tag}>{_inline_markdown(cell.strip())}</{tag}>" for cell in row)
            out.append(f"<tr>{cells}</tr>")
        out.append("</table>")
        in_table = False
        table_rows = []

    for raw in lines:
        line = raw.rstrip()
        stripped = line.strip()

        if stripped.startswith("```"):
            flush_ul()
            flush_table()
            if in_code:
                flush_code()
            else:
                in_code = True
                code_lines = []
            continue

        if in_code:
            code_lines.append(line)
            continue

        if "|" in stripped and stripped.startswith("|") and stripped.endswith("|"):
            flush_ul()
            cells = [cell.strip() for cell in stripped.strip("|").split("|")]
            if len(cells) > 1 and not all(set(cell) <= {"-", ":"} for cell in cells):
                in_table = True
                table_rows.append(cells)
            continue
        flush_table()

        if not stripped:
            flush_ul()
            continue

        heading = re.match(r"^(#{1,6})\s+(.+)$", stripped)
        if heading:
            flush_ul()
            level = len(heading.group(1))
            out.append(f"<h{level}>{_inline_markdown(heading.group(2))}</h{level}>")
            continue

        image = re.match(r"^!\[(.*?)\]\((.*?)\)$", stripped)
        if image:
            flush_ul()
            alt = html.escape(image.group(1))
            src = html.escape(image.group(2))
            out.append(f'<figure><img src="{src}" alt="{alt}"><figcaption>{alt}</figcaption></figure>')
            continue

        if stripped.startswith(("- ", "* ")):
            if not in_ul:
                out.append("<ul>")
                in_ul = True
            out.append(f"<li>{_inline_markdown(stripped[2:].strip())}</li>")
            continue

        flush_ul()
        out.append(f"<p>{_inline_markdown(stripped)}</p>")

    flush_ul()
    flush_table()
    flush_code()
    return "\n".join(out)


def render_html(markdown: str, css: str, title: str) -> str:
    body = markdown_to_html_body(markdown)
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <style>{css}</style>
</head>
<body>
  <main class="page">
{body}
  </main>
</body>
</html>
"""


def render_pdf_from_html(html_path: Path, output_path: Path) -> bool:
    try:
        from weasyprint import HTML  # type: ignore

        HTML(filename=str(html_path)).write_pdf(str(output_path))
        return True
    except Exception:
        pass

    try:
        from playwright.sync_api import sync_playwright  # type: ignore

        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.goto(html_path.resolve().as_uri(), wait_until="networkidle")
            page.pdf(path=str(output_path), print_background=True, format="A4")
            browser.close()
        return True
    except Exception:
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Render financial report Markdown to Markdown, HTML, or PDF.")
    parser.add_argument("--input", required=True, help="Input Markdown file.")
    parser.add_argument("--output", required=True, help="Output file path.")
    parser.add_argument("--format", choices=["markdown", "md", "html", "pdf"], required=True)
    parser.add_argument("--title", default="Financial Research Report")
    parser.add_argument("--css", default=None, help="Optional CSS file. Defaults to skill assets/report.css.")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    markdown = input_path.read_text(encoding="utf-8")

    if args.format in {"markdown", "md"}:
        output_path.write_text(markdown, encoding="utf-8")
        return 0

    skill_root = Path(__file__).resolve().parents[1]
    css_path = Path(args.css) if args.css else skill_root / "assets" / "report.css"
    css = css_path.read_text(encoding="utf-8") if css_path.exists() else ""
    html_text = render_html(markdown, css, args.title)

    if args.format == "html":
        output_path.write_text(html_text, encoding="utf-8")
        return 0

    html_path = output_path.with_suffix(".html")
    html_path.write_text(html_text, encoding="utf-8")
    if render_pdf_from_html(html_path, output_path):
        return 0

    print(
        f"PDF backend unavailable. HTML was written to {html_path}. "
        "Install weasyprint or playwright to enable PDF rendering.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
