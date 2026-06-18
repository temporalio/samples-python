# MCP

Give Gemini access to an [MCP](https://modelcontextprotocol.io/) server's tools.
The worker launches the `echo_mcp_server.py` stdio server and registers it with
the plugin under the name `echo`. Inside the workflow, a
`TemporalMcpClientSession("echo")` is passed as a tool — Gemini's AFC loop
discovers and calls its tools, and `list_tools` / `call_tool` run as Temporal
activities against a pooled worker-side connection.

## What This Sample Demonstrates

- Registering an MCP server with `GoogleGenAIPlugin(mcp_servers={...})`
- Passing `TemporalMcpClientSession(name)` as a `generate_content` tool
- `cache_tools=True` to discover the tool list once and reuse it (replay-safe)
- MCP tool calls dispatched through per-server Temporal activities

## Running the Sample

Prerequisites: install dependencies, set `GOOGLE_API_KEY`, and start a Temporal
dev server. See the [suite README](../README.md).

```bash
# Terminal 1
uv run google_genai_plugin/mcp/run_worker.py

# Terminal 2
uv run google_genai_plugin/mcp/run_workflow.py
```

## Files

| File | Description |
|------|-------------|
| `echo_mcp_server.py` | A minimal `FastMCP` stdio server exposing an `echo` tool |
| `workflow.py` | `McpWorkflow` — passes `TemporalMcpClientSession("echo")` as a tool |
| `run_worker.py` | Registers the `echo` MCP server with the plugin, starts the worker |
| `run_workflow.py` | Executes the workflow and prints the result |
