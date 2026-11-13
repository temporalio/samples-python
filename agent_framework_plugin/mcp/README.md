# MCP

Give the agent the tools of an MCP server. `AgentFrameworkPlugin(mcp_clients={"echo": ...})` registers the server on the Worker. `TemporalMCPToolProvider("echo")` in `Agent(context_providers=[...])` lists the server's tools before each run and turns each call into an Activity:

| Activity | When it runs |
|----------|--------------|
| `temporalio.mcp.echo.list-tools` | Before each `agent.run`, because `cache_tools` defaults to `False` |
| `temporalio.mcp.echo.call-tool` | Each time the model calls a tool of the server |

The included `echo_mcp_server.py` is a one-tool server built on the MCP Python SDK's `MCPServer`. The Worker starts it over stdio with `sys.executable` on the first MCP Activity and keeps the connection for 5 minutes of idleness. Swap in any MCP server by changing the factory in `run_worker.py`.

This sample is its own uv project. The plugin's MCP support needs MCP Python SDK 2, and other samples in this repository still pin SDK 1, so the two cannot share one lock file.

## What this sample demonstrates

- `AgentFrameworkPlugin(mcp_clients=...)` with a factory that returns an `mcp.Client`
- `TemporalMCPToolProvider` as a context provider, with a 30-second start-to-close timeout for its list and call Activities
- The model sees the server's tool schema; the server's connection never leaves the Worker

## Running the sample

Prerequisites: Python 3.11 or later, `OPENAI_API_KEY` in the Worker's environment, and a Temporal dev server (`temporal server start-dev`). Change to this directory first:

```bash
cd agent_framework_plugin/mcp
uv sync
```

```bash
# Terminal 1
uv run run_worker.py

# Terminal 2
uv run run_workflow.py
```

The Worker spawns the server itself. The starter prints the agent's answer, and the Workflow `agent-framework-mcp` shows one `temporalio.mcp.echo.list-tools`, two `agent_framework.invoke_model` and one `temporalio.mcp.echo.call-tool` Activity.

## Tests

`uv run poe test` runs the Workflow against the plugin's scripted chat client and the real echo server, with no API key. `uv run poe lint` runs ruff and mypy.

## Files

| File | Description |
|------|-------------|
| `echo_mcp_server.py` | `MCPServer` with one `echo` tool, served over stdio |
| `workflow.py` | `MCPWorkflow` with `TemporalMCPToolProvider("echo")` |
| `run_worker.py` | Registers the chat client and the MCP server factories, starts the Worker |
| `run_workflow.py` | Executes the Workflow and prints the result |
| `tests/mcp_test.py` | Asserts on the model and MCP Activities in the history |
