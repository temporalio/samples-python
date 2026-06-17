# MCP — MCP Tools as Activities

An agent backed by `TemporalMcpToolSet("filesystem", ...)`, with the worker's
plugin configured as
`GoogleAdkPlugin(toolset_providers=[TemporalMcpToolSetProvider("filesystem", filesystem_toolset)])`.
The shared factory in [`toolsets.py`](./toolsets.py) builds an `McpToolset` over
the [`@modelcontextprotocol/server-filesystem`](https://www.npmjs.com/package/@modelcontextprotocol/server-filesystem)
stdio server, exposing this sample's own directory.

The MCP server's `list-tools` and `call-tool` operations run as Temporal
activities (`filesystem-list-tools` / `filesystem-call-tool`), so the server is
touched only from activity context — never inside the workflow sandbox. The
`not_in_workflow_toolset` factory lets the same agent also run locally, outside
a workflow.

## Requires Node.js / npx (run-it-yourself only)

This scenario shells out to `npx` to start the filesystem MCP server, so it
needs Node.js on your `PATH`. It is not wired into any automated test harness —
run it yourself to try it.

Also review the [prerequisites in the suite README](../README.md) (Temporal dev
server, `uv sync --group google-adk`, and `export GOOGLE_API_KEY=...`).

## Running

Start the worker in one terminal:

```bash
uv run python -m google_adk_agents.mcp.run_worker
```

Then start the workflow in another terminal:

```bash
uv run python -m google_adk_agents.mcp.run_filesystem_workflow
```

## What to expect

The starter asks what files are in the exposed directory. The agent calls the
filesystem MCP tool and prints a description of the directory contents.

## In the Temporal UI

Open the workflow `google-adk-agents-mcp-workflow-id`. The history shows a
`filesystem-list-tools` activity (discovering the MCP tools), `invoke_model`
activities for the model turns, and a `filesystem-call-tool` activity for each
tool the model invokes. The MCP subprocess only ever runs inside those
activities.
