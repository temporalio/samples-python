# MCP

Connect a Strands agent to an [MCP](https://modelcontextprotocol.io/) server through `TemporalMCPClient`. The plugin opens the MCP session at worker startup, enumerates tools, and dispatches each tool call through a dedicated `<server>-call-tool` Temporal activity.

The included `echo_mcp_server.py` is a one-tool FastMCP server (returns the message it was given). Swap it for any real MCP server (filesystem, Postgres, GitHub, etc.) by changing the factory in `run_worker.py`.

## What This Sample Demonstrates

- Registering an MCP server with `StrandsPlugin(mcp_clients=...)`
- Referencing it from a workflow via `TemporalMCPClient(server="...")`
- Running MCP tool calls as durable Temporal activities

## Running the Sample

```bash
# Terminal 1
uv run strands_plugin/mcp/run_worker.py

# Terminal 2
uv run strands_plugin/mcp/run_workflow.py
```

The worker spawns `echo_mcp_server.py` itself; you don't need to start it separately. The Temporal UI will show one `invoke_model` per agent turn plus `echo-call-tool` activities for each MCP tool invocation.

## Files

| File | Description |
|------|-------------|
| `echo_mcp_server.py` | FastMCP server exposing a single `echo` tool |
| `workflow.py` | `MCPWorkflow` with `TemporalMCPClient(server="echo")` |
| `run_worker.py` | Spawns the MCP server and starts the worker |
| `run_workflow.py` | Executes the workflow and prints the result |
