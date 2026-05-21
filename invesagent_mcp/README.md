# InvesAgent MCP

Standalone MCP server for InvesAgent. This package embeds `invesagent_core`, which contains provider adapters, unified models, services, metrics, chart generation, storage helpers, and configuration.

The package can be copied and installed independently because the finance core lives inside this package under `src/invesagent_core`.

Current tool groups:

```text
health / project info
instrument resolution
OHLCV market data and price-volume analysis
chart generation
valuation data and valuation analysis
fundamentals data and fundamentals analysis
benchmark and multi-instrument comparison
industry list and industry members
```

Run with stdio:

```powershell
python -m invesagent_mcp.server --transport stdio
```

Run with Streamable HTTP:

```powershell
python -m invesagent_mcp.server --transport streamable-http --host 127.0.0.1 --port 8000 --path /mcp
```
