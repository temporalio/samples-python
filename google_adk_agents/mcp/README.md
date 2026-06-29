# MCP — MCP Tools as Activities

An agent backed by `TemporalMcpToolSet("echo", ...)`, with the worker's plugin
configured as
`GoogleAdkPlugin(toolset_providers=[TemporalMcpToolSetProvider("echo", echo_toolset)])`.
The shared factory in [`toolsets.py`](./toolsets.py) builds an `McpToolset` over
the in-repo [`echo_mcp_server.py`](./echo_mcp_server.py), a one-tool FastMCP
server that echoes back the message it is given.

The MCP server's `list-tools` and `call-tool` operations run as Temporal
activities (`echo-list-tools` / `echo-call-tool`), so the server is touched only
from activity context, never inside the workflow sandbox. The
`not_in_workflow_toolset` factory lets the same agent also run locally, outside a
workflow.

## Self-contained, no Node required

The echo server is a small Python script launched as a subprocess with the
current interpreter (`sys.executable`), so there is nothing to install and no
network access. Swap `echo_mcp_server.py` for any real MCP server (filesystem,
Postgres, GitHub, etc.) by changing the factory in `toolsets.py`.

Also review the [prerequisites in the suite README](../README.md) (Temporal dev
server, `uv sync --group google-adk`, and `export GOOGLE_API_KEY=...`).

## Running

Start the worker in one terminal:

```bash
uv run python -m google_adk_agents.mcp.run_worker
```

Then start the workflow in another terminal:

```bash
uv run python -m google_adk_agents.mcp.run_echo_workflow
```

The worker spawns `echo_mcp_server.py` itself; you don't need to start it
separately.

## What to expect

The starter asks the agent to echo `hello from MCP`. The agent calls the echo
MCP tool and reports back when it's done.

## In the Temporal UI

Open the workflow `google-adk-agents-mcp-workflow-id`. The history shows an
`echo-list-tools` activity (discovering the MCP tools), `invoke_model`
activities for the model turns, and an `echo-call-tool` activity for each tool
the model invokes. The MCP subprocess only ever runs inside those activities.
