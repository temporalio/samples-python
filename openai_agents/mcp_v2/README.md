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
uv run python tools_server.py
```

Then start the Temporal worker:

```bash
uv run python run_worker.py
```

Finally, run the workflow:

```bash
uv run python run_workflow.py
```
