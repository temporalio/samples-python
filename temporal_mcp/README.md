# Durable MCP clients

This standalone project demonstrates
[`temporalio-mcp` 0.2.0](https://pypi.org/project/temporalio-mcp/), which lets
Temporal Workflow code call MCP tools, prompts, and resources through durable
Activities. The real MCP client, transport, network connections, and credentials
remain on the Worker.

The same Workflow is available over three MCP SDK v2 client forms:

- `in-process` constructs the MCP server directly inside the Worker process.
- `stdio` lets the Worker launch and manage `server.py` as a subprocess.
- `streamable-http` connects the Worker to a separately running HTTP server.

## Prerequisites

- Python 3.10 or newer and [uv](https://docs.astral.sh/uv/)
- A local Temporal server: `temporal server start-dev`

Change to this directory and install the locked environment:

```bash
cd temporal_mcp
uv sync --locked --all-groups
```

## Run a sample

For the in-process transport, start the Worker and Workflow in separate shells:

```bash
uv run run_worker.py in-process
uv run run_workflow.py in-process
```

The stdio transport uses the same commands. The Worker launches `server.py`
automatically with the current Python interpreter:

```bash
uv run run_worker.py stdio
uv run run_workflow.py stdio
```

Streamable HTTP needs a third shell for the MCP server:

```bash
uv run server.py streamable-http
uv run run_worker.py streamable-http
uv run run_workflow.py streamable-http
```

The HTTP server defaults to `http://127.0.0.1:8000/mcp`. Use `--host` and
`--port` on `server.py` and `--http-url` on `run_worker.py` to change it.

## What the Workflow demonstrates

`MCPDemoWorkflow` lists and calls tools, lists and gets prompts, and lists and
reads both static and templated resources. Each MCP operation is a Temporal
Activity. The second `list_tools()` call uses the Workflow client's replay-safe
cache and does not schedule another Activity.

The sample bounds each Activity attempt and the complete retry series. MCP tools
still have at-least-once execution semantics, so tools with side effects should
accept a stable idempotency key. Resolve URLs, tokens, and other secrets in the
worker-side client factory rather than putting them in Workflow inputs or the
factory argument, where they would be recorded in Workflow history.

Run all three transports end-to-end against a local Temporal test server with:

```bash
uv run poe test
```
