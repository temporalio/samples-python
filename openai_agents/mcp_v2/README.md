# MCP v2 Example

This sample integrates an MCP SDK v2 streamable HTTP server with an OpenAI
agent running in a Temporal workflow. The worker registers a named server
factory with `OpenAIAgentsPlugin(mcp_servers=...)`, and the workflow creates a
durable proxy with `temporal_mcp_server(...)`.

Review the integration [prerequisites](../README.md#prerequisites), including a
running Temporal dev server and an `OPENAI_API_KEY`, before running the sample.

The sample has its own uv project because other samples still require MCP SDK
v1. Run these commands from the repository root.

First, start the MCP server:

```bash
uv run --project openai_agents/mcp_v2 --locked \
  python -m openai_agents.mcp_v2.tools_server
```

Then start the Temporal worker:

```bash
uv run --project openai_agents/mcp_v2 --locked \
  python -m openai_agents.mcp_v2.run_worker
```

Finally, run the workflow:

```bash
uv run --project openai_agents/mcp_v2 --locked \
  python -m openai_agents.mcp_v2.run_workflow
```
