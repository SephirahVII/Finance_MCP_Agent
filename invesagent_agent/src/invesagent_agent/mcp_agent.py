from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

from agents import Agent, OpenAIChatCompletionsModel, Runner, set_tracing_disabled
from agents.mcp import MCPServerStdio
from openai import AsyncOpenAI

from invesagent_agent.prompts.financial_analyst import FINANCIAL_ANALYST_INSTRUCTIONS


AGENT_PROJECT_ROOT = Path(__file__).resolve().parents[3]
MCP_PROJECT_ROOT = AGENT_PROJECT_ROOT.parent / "invesagent_mcp"


def _load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_env_file(AGENT_PROJECT_ROOT / ".env")
_load_env_file(AGENT_PROJECT_ROOT.parent / ".env")


def _getenv(name: str, default: str | None = None) -> str | None:
    return os.getenv(name) or default


def get_llm_api_key() -> str:
    """Return the API key for the configured LLM provider."""
    provider = (_getenv("LLM_PROVIDER", "openai") or "openai").lower()

    key = {
        "openai": _getenv("OPENAI_API_KEY"),
        "deepseek": _getenv("DEEPSEEK_API_KEY"),
        "minimax": _getenv("MINIMAX_API_KEY"),
        "qwen": _getenv("QWEN_API_KEY"),
    }.get(provider)

    if key is None:
        raise ValueError(f"Unsupported LLM_PROVIDER: {provider}")
    if not key:
        raise RuntimeError(f"API key is missing for LLM provider: {provider}")

    return key


def get_llm_model_name() -> str:
    """Return the configured model name or a provider-specific default."""
    configured = _getenv("LLM_MODEL") or _getenv("MODEL_NAME")
    if configured:
        return configured

    provider = (_getenv("LLM_PROVIDER", "openai") or "openai").lower()
    defaults = {
        "openai": "gpt-4.1-mini",
        "deepseek": "deepseek-v4-flash",
        "minimax": "MiniMax-M1",
        "qwen": "qwen-plus",
    }
    return defaults.get(provider, "gpt-4.1-mini")


def build_agent_model() -> OpenAIChatCompletionsModel:
    """Build an OpenAI-compatible chat completions model for the Agent SDK."""
    provider = (_getenv("LLM_PROVIDER", "openai") or "openai").lower()

    if provider != "openai":
        set_tracing_disabled(True)

    client = AsyncOpenAI(
        api_key=get_llm_api_key(),
        base_url=_getenv("LLM_BASE_URL"),
    )

    return OpenAIChatCompletionsModel(
        model=get_llm_model_name(),
        openai_client=client,
    )


async def run_financial_agent(user_query: str) -> str:
    """Run the financial analyst agent with the local MCP server."""
    env = os.environ.copy()
    mcp_python_path = _getenv("MCP_PYTHON_PATH") or sys.executable

    print("[1/5] 正在启动本地 MCP Server...")
    async with MCPServerStdio(
        name="InvesAgent Finance MCP",
        params={
            "command": mcp_python_path,
            "args": ["-m", "invesagent_mcp.server"],
            "cwd": str(MCP_PROJECT_ROOT),
            "env": env,
        },
        cache_tools_list=True,
    ) as mcp_server:
        print("[2/5] MCP Server 已连接，正在创建 Agent...")

        agent = Agent(
            name="InvesAgent 金融研究助手",
            instructions=FINANCIAL_ANALYST_INSTRUCTIONS,
            model=build_agent_model(),
            mcp_servers=[mcp_server],
        )

        print("[3/5] Agent 已创建，正在执行用户问题...")
        print(f"[问题] {user_query}")

        result = await Runner.run(agent, user_query)
        print("[4/5] Agent 执行完成，正在输出结果...")
        final_output = result.final_output

    print("[5/5] MCP Server 已关闭。")
    return final_output


def main() -> None:
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
    else:
        query = (
            "请分析贵州茅台 2024-01-01 到 2024-01-31 的价格走势，"
            "需要调用工具获取真实数据，说明收益率、波动率、最大回撤，并生成图表。"
        )

    final_output = asyncio.run(run_financial_agent(query))
    print(final_output)


if __name__ == "__main__":
    main()
