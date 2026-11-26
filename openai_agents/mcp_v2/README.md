# MCP v2 Example

This sample integrates an MCP SDK v2 streamable HTTP server with an OpenAI
agent running in a Temporal workflow. The worker registers a named server
factory with `OpenAIAgentsPlugin(mcp_servers=...)`, and the workflow creates a
durable proxy with `temporal_mcp_server(...)`.

Review the integration [prerequisites](../README.md#prerequisites), including a
running Temporal dev server and an `OPENAI_API_KEY`, before running the sample.

The sample has its own uv project because other samples still require MCP SDK
v1. Change to the sample directory before running it:

```bash
cd openai_agents/mcp_v2
```

First, start the MCP server:

```bash
uv run tools_server.py
```

Then start the Temporal worker:

```bash
uv run run_worker.py
```

Finally, run the workflow:

```bash
uv run run_workflow.py
```

## Use an authenticated remote MCP server

[ClickHouse Loom](https://github.com/ClickHouse/loom) is a self-hosted MCP server
for document search and agent memory. To use it in this sample, set `LOOM_MCP_URL`
to the full `/mcp` URL and `LOOM_TOKEN` to a Loom token. Use a namespace-scoped
viewer token when the workflow only needs to search. Load these environment
variables in the worker process so the bearer token stays out of workflow input
and history.

In a fresh copy of the sample, add `import os` to `run_worker.py` and replace its
server factory:

```python
def streamable_http_server() -> MCPServerStreamableHttp:
    return MCPServerStreamableHttp(
        name=MCP_SERVER_NAME,
        params={
            "url": os.environ["LOOM_MCP_URL"],
            "headers": {"Authorization": f"Bearer {os.environ['LOOM_TOKEN']}"},
        },
    )
```

The named worker factory supplies the connection used by
`temporal_mcp_server(MCP_SERVER_NAME)`. In `workflow.py`, replace the local
sample's three tool requests with a prompt about documents indexed in your Loom
namespace. Skip the local MCP server and start the worker and workflow against Loom. See the [Loom
MCP reference](https://github.com/ClickHouse/loom/blob/main/docs/reference/mcp.md)
for toolsets and authentication.
