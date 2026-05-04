from __future__ import annotations

import sys
import asyncio
import os
from pathlib import Path

from openai import AsyncOpenAI
from agents import Agent, OpenAIChatCompletionsModel, Runner, set_tracing_disabled
from agents.mcp import MCPServerStdio

from src.agent.prompts import FINANCIAL_ANALYST_INSTRUCTIONS
from src.config.settings import settings


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def get_llm_api_key() -> str:
    """Return the API key for the configured LLM provider."""
    provider = settings.llm_provider.lower()

    if provider == "openai":
        key = settings.openai_api_key
    elif provider == "deepseek":
        key = settings.deepseek_api_key
    elif provider == "minimax":
        key = settings.minimax_api_key
    elif provider == "qwen":
        key = settings.qwen_api_key
    else:
        raise ValueError(f"Unsupported LLM_PROVIDER: {settings.llm_provider}")

    if not key:
        raise RuntimeError(f"API key is missing for LLM provider: {provider}")

    return key


def get_llm_model_name() -> str:
    """Return the configured model name or a provider-specific default."""
    if settings.llm_model:
        return settings.llm_model

    provider = settings.llm_provider.lower()
    defaults = {
        "openai": "gpt-4.1-mini",
        "deepseek": "deepseek-v4-flash",
        "minimax": "MiniMax-M1",
        "qwen": "qwen-plus",
    }
    return defaults.get(provider, "gpt-4.1-mini")


def build_agent_model() -> OpenAIChatCompletionsModel:
    """Build an OpenAI-compatible chat completions model for the Agent SDK."""
    provider = settings.llm_provider.lower()

    if provider != "openai":
        set_tracing_disabled(True)

    client = AsyncOpenAI(
        api_key=get_llm_api_key(),
        base_url=settings.llm_base_url,
    )

    return OpenAIChatCompletionsModel(
        model=get_llm_model_name(),
        openai_client=client,
    )


async def run_financial_agent(user_query: str) -> str:
    """Run the financial analyst agent with the local MCP server."""
    env = os.environ.copy()

    if settings.tushare_token:
        env["TUSHARE_TOKEN"] = settings.tushare_token

    print("[1/5] 正在启动本地 MCP Server...")
    async with MCPServerStdio(
        name="Tushare Financial Analyst MCP",
        params={
            "command": settings.mcp_python_path,
            "args": ["-m", "src.mcp_server.server"],
            "cwd": str(PROJECT_ROOT),
            "env": env,
        },
        cache_tools_list=True,
    ) as mcp_server:
        print("[2/5] MCP Server 已连接，正在创建 Agent...")

        agent = Agent(
            name="A股金融分析师",
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
