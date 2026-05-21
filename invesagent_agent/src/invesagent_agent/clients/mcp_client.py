from __future__ import annotations

import json
import os
import sys
from contextlib import ExitStack
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import anyio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


@dataclass(frozen=True)
class MCPToolCall:
    """A serializable MCP tool call request."""

    name: str
    arguments: dict[str, Any]


def _default_mcp_cwd() -> Path:
    """Return the sibling MCP project directory when running from the monorepo."""
    agent_root = Path(__file__).resolve().parents[4]
    sibling = agent_root.parent / "invesagent_mcp"
    return sibling if sibling.exists() else agent_root


def _decode_tool_result(result: Any) -> Any:
    """Decode an MCP CallToolResult into Python data."""
    if getattr(result, "isError", False):
        raise RuntimeError(str(result))

    content = getattr(result, "content", None) or []
    if not content:
        return None

    if len(content) == 1 and hasattr(content[0], "text"):
        text = content[0].text
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return text

    decoded: list[Any] = []
    for item in content:
        if hasattr(item, "text"):
            try:
                decoded.append(json.loads(item.text))
            except json.JSONDecodeError:
                decoded.append(item.text)
        else:
            decoded.append(item)
    return decoded


class InvesAgentMCPClient:
    """Small stdio MCP client for LangGraph workflow nodes."""

    def __init__(
        self,
        command: str | None = None,
        cwd: str | Path | None = None,
        env: dict[str, str] | None = None,
    ) -> None:
        self.command = command or os.getenv("MCP_PYTHON_PATH") or sys.executable
        self.cwd = Path(cwd) if cwd is not None else _default_mcp_cwd()
        self.env = env or os.environ.copy()

    async def call_tool_async(self, name: str, arguments: dict[str, Any] | None = None) -> Any:
        """Call one MCP tool through a stdio MCP server process."""
        params = StdioServerParameters(
            command=self.command,
            args=["-m", "invesagent_mcp.server", "--transport", "stdio"],
            cwd=str(self.cwd),
            env=self.env,
        )

        with ExitStack() as stack:
            errlog = stack.enter_context(open(os.devnull, "w", encoding="utf-8"))
            async with stdio_client(params, errlog=errlog) as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    result = await session.call_tool(name, arguments or {})
                    return _decode_tool_result(result)

    def call_tool(self, name: str, arguments: dict[str, Any] | None = None) -> Any:
        """Synchronous helper for current LangGraph nodes."""
        return anyio.run(self.call_tool_async, name, arguments or {})


_DEFAULT_CLIENT: InvesAgentMCPClient | None = None


def get_mcp_client() -> InvesAgentMCPClient:
    """Return a lazily-created MCP client."""
    global _DEFAULT_CLIENT
    if _DEFAULT_CLIENT is None:
        _DEFAULT_CLIENT = InvesAgentMCPClient()
    return _DEFAULT_CLIENT


def call_mcp_tool(name: str, arguments: dict[str, Any] | None = None) -> Any:
    """Call an MCP tool using the default client."""
    return get_mcp_client().call_tool(name, arguments or {})
