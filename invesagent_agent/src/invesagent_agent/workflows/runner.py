from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Any

from invesagent_agent.outputs import export_report
from invesagent_agent.runtime.memory import MemoryManager
from invesagent_agent.workflows.chat_graph import run_chat_workflow


UI_WIDTH = 96


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the InvesAgent chat and research workflow.")
    parser.add_argument("query", nargs="*", help="User question.")
    parser.add_argument("--market", default="cn", help="Market code, e.g. cn, hk, us.")
    parser.add_argument("--asset-type", default="stock", help="Asset type, e.g. stock, index, etf.")
    parser.add_argument("--provider", default="auto", help="Data provider, e.g. auto, tushare, akshare.")
    parser.add_argument("--industry-member-limit", type=int, default=10)
    parser.add_argument(
        "--history-file",
        default=None,
        help="Optional JSON file used to load and append multi-turn chat history. Overrides --session-id.",
    )
    parser.add_argument(
        "--session-id",
        default=None,
        help=(
            "Session id saved under .runtime/sessions/<session-id>.json when --history-file is omitted. "
            "For --chat, omitting this creates a new timestamped session."
        ),
    )
    parser.add_argument("--show-intent", action="store_true", help="Print routing and task planning details.")
    parser.add_argument("--show-state", action="store_true", help="Print final state keys after the response.")
    parser.add_argument(
        "--output",
        default=None,
        help="Optional report output path. Supported suffixes: .md, .html, .pdf.",
    )
    parser.add_argument(
        "--format",
        choices=["md", "html", "pdf"],
        default=None,
        help="Report export format.",
    )
    parser.add_argument(
        "--no-export-prompt",
        action="store_true",
        help="Do not ask whether to save generated reports after each turn.",
    )
    parser.add_argument(
        "--chat",
        action="store_true",
        help="Start an interactive chat session. Type exit, quit, or q to end.",
    )
    return parser.parse_args()


def _safe_session_id(value: str | None) -> str:
    text = (value or "default").strip() or "default"
    safe = "".join(char if char.isalnum() or char in {"-", "_"} else "_" for char in text)
    return safe or "default"


def _default_session_path(session_id: str | None) -> Path:
    return Path(".runtime") / "sessions" / f"{_safe_session_id(session_id)}.json"


def _new_session_id() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _long_term_memory_path() -> Path:
    return Path(os.getenv("LONG_TERM_MEMORY_FILE", ".runtime/memory/MEMORY.md"))


def _ensure_long_term_memory_file(path: Path) -> None:
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                "# InvesAgent Long-Term Memory",
                "",
                "## User Preferences",
                "- preferred_market: cn",
                "- preferred_language: zh-CN",
                "- prefers_explicit_time_scope: true",
                "",
                "## Watchlist",
                "",
                "## Report Preferences",
                "- Reports should explicitly state data time scope.",
                "- Charts should be placed near the relevant section when possible.",
                "",
            ]
        ),
        encoding="utf-8",
    )


def _load_long_term_memory() -> str:
    path = _long_term_memory_path()
    _ensure_long_term_memory_file(path)
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def _attach_long_term_memory(task_memory: dict) -> dict:
    state = {"task_memory": task_memory if isinstance(task_memory, dict) else {}}
    memory = MemoryManager(state)
    memory.update_long_term(_load_long_term_memory())
    return state["task_memory"]


def _resolve_history_file(args: argparse.Namespace) -> str:
    if args.history_file:
        return args.history_file
    return str(_default_session_path(args.session_id))


def _resolve_session_id(args: argparse.Namespace) -> str:
    if args.session_id:
        return _safe_session_id(args.session_id)
    if args.chat:
        return _new_session_id()
    return "default"


def _text_width(text: str) -> int:
    width = 0
    for char in text:
        if unicodedata.east_asian_width(char) in {"F", "W"}:
            width += 2
        else:
            width += 1
    return width


def _fit_text(text: str, width: int) -> str:
    result = []
    used = 0
    for char in text:
        char_width = 2 if unicodedata.east_asian_width(char) in {"F", "W"} else 1
        if used + char_width > width:
            break
        result.append(char)
        used += char_width
    return "".join(result) + (" " * max(width - used, 0))


def _wrap_text(text: str, width: int) -> list[str]:
    if not text:
        return [""]

    wrapped: list[str] = []
    current: list[str] = []
    used = 0
    for char in text:
        char_width = 2 if unicodedata.east_asian_width(char) in {"F", "W"} else 1
        if used + char_width > width and current:
            wrapped.append("".join(current))
            current = [char]
            used = char_width
            continue
        current.append(char)
        used += char_width
    if current:
        wrapped.append("".join(current))
    return wrapped


def _box(lines: list[str], title: str | None = None, width: int = UI_WIDTH) -> str:
    inner_width = width - 4
    top_label = f" {title} " if title else ""
    top_padding = max(width - 2 - _text_width(top_label), 0)
    top = "+" + top_label + ("-" * top_padding) + "+"
    display_lines = []
    for line in lines:
        display_lines.extend(_wrap_text(line, inner_width))
    body = [f"| {_fit_text(line, inner_width)} |" for line in display_lines]
    bottom = "+" + ("-" * (width - 2)) + "+"
    return "\n".join([top, *body, bottom])


def _section(title: str, content: Any) -> str:
    if isinstance(content, (dict, list)):
        text = json.dumps(content, ensure_ascii=False, indent=2, default=str)
    else:
        text = str(content)
    lines = text.splitlines() or [""]
    return _box(lines, title=title)


def _git_branch() -> str:
    try:
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=Path.cwd(),
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return "unknown"
    return result.stdout.strip() or "unknown"


def _render_banner(args: argparse.Namespace, mode: str) -> None:
    workspace = str(Path.cwd())
    provider = os.getenv("LLM_PROVIDER", "openai")
    model = (
        os.getenv(f"{provider.upper()}_MODEL")
        or os.getenv("LLM_MODEL")
        or os.getenv("MODEL_NAME")
        or "default"
    )
    history = args.history_file or "off"

    logo = [
        r" ___                         _                    _   ",
        r"|_ _|_ ____   _____  ___    / \   __ _  ___ _ __ | |_ ",
        r" | || '_ \ \ / / _ \/ __|  / _ \ / _` |/ _ \ '_ \| __|",
        r" | || | | \ V /  __/\__ \ / ___ \ (_| |  __/ | | | |_ ",
        r"|___|_| |_|\_/ \___||___//_/   \_\__, |\___|_| |_|\__|",
        r"                                  |___/               ",
        "",
        "Invesagent",
        "investment & analysis agent",
        "-" * 72,
        f"WORKSPACE  {workspace}",
        f"MODEL      {model}",
        f"PROVIDER   {provider}",
        f"BRANCH     {_git_branch()}",
        f"MODE       {mode}",
        f"MARKET     {args.market}",
        f"ASSET      {args.asset_type}",
        f"MCP        provider={args.provider}",
        f"HISTORY    {history}",
        "-" * 72,
        "中文：Invesagent 是一个本地化的投资与分析 Agent，可在本机调用 MCP 数据工具，",
        "      获取行情、财务、估值和行业数据，并组织多 Agent 生成研究分析与报告。",
        "EN:   Invesagent is a local investment and analysis agent. It can call MCP",
        "      data tools for market, fundamentals, valuation, and industry research,",
        "      then coordinate multiple agents to produce analysis and reports.",
        "-" * 72,
        "输入 exit / quit / q 结束会话。",
    ]
    print()
    print(_box(logo))


def _load_session(path: str | None, query: str) -> tuple[list[dict[str, str]], dict]:
    if not path:
        return ([{"role": "user", "content": query}] if query else []), _attach_long_term_memory({})

    history_path = Path(path)
    if not history_path.exists():
        return ([{"role": "user", "content": query}] if query else []), _attach_long_term_memory({})

    try:
        value = json.loads(history_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ([{"role": "user", "content": query}] if query else []), _attach_long_term_memory({})

    messages = value if isinstance(value, list) else value.get("messages", [])
    task_memory = {} if isinstance(value, list) else value.get("task_memory", {})
    if not isinstance(messages, list):
        messages = []
    if not isinstance(task_memory, dict):
        task_memory = {}

    cleaned = [
        {"role": str(item.get("role", "user")), "content": str(item.get("content", ""))}
        for item in messages
        if isinstance(item, dict) and item.get("content")
    ]
    if query:
        cleaned = [*cleaned[-20:], {"role": "user", "content": query}]
    else:
        cleaned = cleaned[-20:]
    return cleaned, _attach_long_term_memory(task_memory)


def _save_session(
    path: str | None,
    messages: list[dict[str, str]],
    task_memory: dict,
    session_id: str | None = None,
) -> None:
    if not path:
        return

    history_path = Path(path)
    history_path.parent.mkdir(parents=True, exist_ok=True)
    memory = MemoryManager({"task_memory": task_memory if isinstance(task_memory, dict) else {}}).root()
    history_path.write_text(
        json.dumps(
            {
                "session_id": session_id or history_path.stem,
                "messages": messages[-40:],
                "task_memory": memory,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def _infer_export_format(path: Path, selected_format: str | None) -> str:
    if selected_format:
        return selected_format
    suffix = path.suffix.lower().lstrip(".")
    if suffix in {"md", "markdown"}:
        return "md"
    if suffix == "html":
        return "html"
    if suffix == "pdf":
        return "pdf"
    return "md"


def _default_report_path(output_format: str) -> Path:
    suffix = "html" if output_format == "html" else "pdf" if output_format == "pdf" else "md"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    reports_dir = Path(os.getenv("REPORTS_DIR", ".runtime/reports") or ".runtime/reports")
    return reports_dir / f"invesagent_report_{timestamp}.{suffix}"


def _report_title(research_state: dict[str, Any]) -> str:
    context = research_state.get("report_context", {})
    company = context.get("company", {}) if isinstance(context, dict) else {}
    name = company.get("name") or company.get("symbol")
    if name:
        return f"InvesAgent Report - {name}"
    return "InvesAgent Report"


def _export_report(
    *,
    research_state: dict[str, Any],
    output_path: Path,
    output_format: str,
) -> Path | None:
    report = research_state.get("final_report") or research_state.get("draft_report")
    if not report:
        print(_section("Report Export", "本轮没有可保存的报告内容。"))
        return None

    saved_path = export_report(
        report=str(report),
        output_path=output_path,
        output_format=output_format,
        report_context=research_state.get("report_context", {}),
        title=_report_title(research_state),
    )
    print(_section("Report Export", f"已保存：{saved_path}"))
    return saved_path


def _maybe_export_report(result: dict[str, Any], args: argparse.Namespace) -> None:
    research_state = result.get("research_state") or {}
    if not isinstance(research_state, dict):
        return
    task_action = research_state.get("task_plan", {}).get("action")
    if task_action != "execute" or not research_state.get("report_context"):
        return
    if not (research_state.get("final_report") or research_state.get("draft_report")):
        return

    if args.output:
        output_path = Path(args.output)
        output_format = _infer_export_format(output_path, args.format)
        if output_path.suffix == "":
            output_path = output_path.with_suffix(
                ".html" if output_format == "html" else ".pdf" if output_format == "pdf" else ".md"
            )
        _export_report(
            research_state=research_state,
            output_path=output_path,
            output_format=output_format,
        )
        return

    if args.no_export_prompt or not sys.stdin.isatty():
        return

    choice = input("\n是否保存本轮报告？输入 md / html / pdf，或直接回车跳过：").strip().lower()
    if not choice or choice in {"skip", "no", "n"}:
        return
    if choice not in {"md", "html", "pdf"}:
        print(_section("Report Export", "未识别的格式，已跳过保存。"))
        return
    _export_report(
        research_state=research_state,
        output_path=_default_report_path(choice),
        output_format=choice,
    )


def _run_one_turn(
    query: str,
    args: argparse.Namespace,
    messages: list[dict[str, str]],
    task_memory: dict,
) -> tuple[list[dict[str, str]], dict]:
    try:
        result = run_chat_workflow(
            user_query=query,
            market=args.market,
            asset_type=args.asset_type,
            provider=args.provider,
            industry_member_limit=args.industry_member_limit,
            messages=messages,
            task_memory=task_memory,
        )
    except Exception as exc:
        final_response = (
            "本轮执行遇到错误，聊天会话仍然保留。"
            f"\n错误摘要：{type(exc).__name__}: {exc}"
            "\n你可以补充更明确的标的、时间范围，或重新提问。"
        )
        print(f"\n{final_response}")
        messages = [*messages, {"role": "assistant", "content": final_response}]
        return messages, task_memory

    final_response = result.get("final_response") or "No response generated."
    messages = [*messages, {"role": "assistant", "content": final_response}]
    task_memory = result.get("task_memory", task_memory)
    print(f"\n{final_response}")
    _maybe_export_report(result, args)

    if args.show_intent:
        print()
        print(_section("General Assistant Decision", result.get("general_decision", {})))
        if task_memory:
            print()
            print(_section("Task Memory", task_memory))
        research_state = result.get("research_state") or {}
        if research_state.get("task_plan"):
            print()
            print(_section("Investment Task Plan", research_state.get("task_plan", {})))

    if args.show_state:
        print()
        print(_section("Final State Keys", sorted(result.keys())))

    return messages, task_memory


def _run_interactive_chat(args: argparse.Namespace) -> None:
    messages, task_memory = _load_session(args.history_file, "")

    _render_banner(args, mode="interactive chat")

    while True:
        try:
            query = input("\ninvesagent> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n已退出 Invesagent chat。")
            break

        if query.lower() in {"exit", "quit", "q"}:
            print("本次对话已结束。")
            break
        if not query:
            continue

        messages = [*messages, {"role": "user", "content": query}]
        messages, task_memory = _run_one_turn(
            query=query,
            args=args,
            messages=messages,
            task_memory=task_memory,
        )
        _save_session(args.history_file, messages, task_memory, session_id=args.session_id)


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    args = parse_args()
    args.session_id = _resolve_session_id(args)
    args.history_file = _resolve_history_file(args)
    if args.chat:
        _run_interactive_chat(args)
        return

    query = " ".join(args.query).strip()
    if not query:
        query = "你好，请介绍一下 InvesAgent 可以做什么。"

    messages, task_memory = _load_session(args.history_file, query)
    _render_banner(args, mode="single turn")
    print(f"\ninvesagent> {query}")
    updated_messages, updated_memory = _run_one_turn(
        query=query,
        args=args,
        messages=messages,
        task_memory=task_memory,
    )
    _save_session(args.history_file, updated_messages, updated_memory, session_id=args.session_id)


if __name__ == "__main__":
    main()
