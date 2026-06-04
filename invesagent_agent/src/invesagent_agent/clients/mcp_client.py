from __future__ import annotations

import json
import os
import sys
from contextlib import ExitStack, asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import anyio
from anyio.from_thread import BlockingPortal, start_blocking_portal
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
        self._portal_cm = None
        self._portal: BlockingPortal | None = None
        self._session_cm = None
        self._session: ClientSession | None = None
        self._opened = False

    def _server_params(self) -> StdioServerParameters:
        return StdioServerParameters(
            command=self.command,
            args=["-m", "invesagent_mcp.server", "--transport", "stdio"],
            cwd=str(self.cwd),
            env=self.env,
        )

    @asynccontextmanager
    async def _session_context(self):
        with open(os.devnull, "w", encoding="utf-8") as errlog:
            async with stdio_client(self._server_params(), errlog=errlog) as (
                read_stream,
                write_stream,
            ):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    yield session

    async def _open_async(self) -> None:
        """Open one-shot async session when used without a blocking portal."""
        if self._session is not None:
            return

        context = self._session_context()
        session = await context.__aenter__()
        self._session_cm = context
        self._session = session

    async def _close_async(self) -> None:
        if self._session_cm is not None:
            await self._session_cm.__aexit__(None, None, None)
        self._session_cm = None
        self._session = None

    async def _call_tool_on_session_async(
        self,
        name: str,
        arguments: dict[str, Any] | None = None,
    ) -> Any:
        await self._open_async()
        if self._session is None:
            raise RuntimeError("MCP session is not initialized.")
        result = await self._session.call_tool(name, arguments or {})
        return _decode_tool_result(result)

    def open(self) -> None:
        """Open a persistent stdio MCP server/session for repeated tool calls."""
        if self._opened:
            return
        self._portal_cm = start_blocking_portal()
        self._portal = self._portal_cm.__enter__()
        self._session_cm = self._portal.wrap_async_context_manager(self._session_context())
        self._session = self._session_cm.__enter__()
        self._opened = True

    def close(self) -> None:
        """Close the persistent MCP session and server process if opened."""
        if not self._opened:
            return
        try:
            if self._session_cm is not None:
                self._session_cm.__exit__(None, None, None)
        finally:
            self._session_cm = None
            self._session = None
            if self._portal_cm is not None:
                self._portal_cm.__exit__(None, None, None)
            self._portal_cm = None
            self._portal = None
            self._opened = False

    def __enter__(self) -> "InvesAgentMCPClient":
        self.open()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    async def call_tool_async(self, name: str, arguments: dict[str, Any] | None = None) -> Any:
        """Call one MCP tool through a stdio MCP server process."""
        with ExitStack() as stack:
            errlog = stack.enter_context(open(os.devnull, "w", encoding="utf-8"))
            async with stdio_client(self._server_params(), errlog=errlog) as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    result = await session.call_tool(name, arguments or {})
                    return _decode_tool_result(result)

    def call_tool(self, name: str, arguments: dict[str, Any] | None = None) -> Any:
        """Synchronous helper for current LangGraph nodes."""
        if self._opened:
            if self._portal is None:
                raise RuntimeError("MCP blocking portal is not initialized.")
            return self._portal.call(self._call_tool_on_session_async, name, arguments or {})
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
