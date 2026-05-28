from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from invesagent_agent.clients.mcp_client import InvesAgentMCPClient


class ToolClient(Protocol):
    """Minimal interface used by agent nodes to call external tools."""

    def call_tool(self, name: str, arguments: dict[str, Any] | None = None) -> Any:
        ...


@dataclass
class StdioMCPToolClient:
    """ToolClient backed by the local stdio MCP client."""

    mcp_client: InvesAgentMCPClient = field(default_factory=InvesAgentMCPClient)

    def call_tool(self, name: str, arguments: dict[str, Any] | None = None) -> Any:
        return self.mcp_client.call_tool(name, arguments or {})


_DEFAULT_TOOL_CLIENT: ToolClient | None = None


def get_default_tool_client() -> ToolClient:
    global _DEFAULT_TOOL_CLIENT
    if _DEFAULT_TOOL_CLIENT is None:
        _DEFAULT_TOOL_CLIENT = StdioMCPToolClient()
    return _DEFAULT_TOOL_CLIENT


def set_default_tool_client(client: ToolClient | None) -> None:
    global _DEFAULT_TOOL_CLIENT
    _DEFAULT_TOOL_CLIENT = client


def get_tool_client(value: Any = None) -> ToolClient:
    if value is not None and hasattr(value, "call_tool"):
        return value
    return get_default_tool_client()
