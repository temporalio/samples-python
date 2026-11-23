# MCP

Connect a Strands agent to an [MCP](https://modelcontextprotocol.io/) server through `TemporalMCPClient`. The agent lists the server's tools in a `temporalio.mcp.<server>.list-tools` activity before each model call, and runs each tool call in a `temporalio.mcp.<server>.call-tool` activity. MCP needs the `mcp` extra, `temporalio-strands-agents[mcp]`, and the MCP Python SDK v2.

The included `echo_mcp_server.py` is a one-tool MCP server (returns the message it was given). Swap it for any real MCP server (filesystem, Postgres, GitHub, etc.) by changing the factory in `run_worker.py`. The factory returns a new `mcp.Client` each time it's called. Options such as `prefix` and `tool_filters` go on `TemporalMCPClient` in the workflow.

## What This Sample Demonstrates

- Registering an MCP server with `StrandsPlugin(mcp_clients=...)` and an `mcp.Client` factory
- Referencing it from a workflow via `TemporalMCPClient(server="...")`
- Running MCP tool calls as durable Temporal activities

## Running the Sample

```bash
# Terminal 1
uv run strands_plugin/mcp/run_worker.py

# Terminal 2
uv run strands_plugin/mcp/run_workflow.py
```

The worker spawns `echo_mcp_server.py` itself; you don't need to start it separately. The Temporal UI will show one `invoke_model` per agent turn, a `temporalio.mcp.echo.list-tools` activity before each, and a `temporalio.mcp.echo.call-tool` activity for each MCP tool invocation.

## Files

| File | Description |
|------|-------------|
| `echo_mcp_server.py` | MCP server exposing a single `echo` tool |
| `workflow.py` | `MCPWorkflow` with `TemporalMCPClient(server="echo")` |
| `run_worker.py` | Spawns the MCP server and starts the worker |
| `run_workflow.py` | Executes the workflow and prints the result |
