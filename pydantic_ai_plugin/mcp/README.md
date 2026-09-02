# MCP

The agent uses a stateless in-process FastMCP server. `MCPToolset` exposes its `support_hours` tool, while `TemporalDurability` moves MCP listing and tool calls into Temporal Activities. The server keeps no session state, so Activity retries are safe.

```bash
uv run pydantic_ai_plugin/mcp/run_worker.py
temporal workflow execute --type MCPWorkflow --task-queue pydantic-ai-mcp --workflow-id pydantic-ai-mcp-1 --input '{"prompt":"When is support staffed?","model":null}'
```

Use `"model":"gateway/openai:gpt-5.2"` for a live run.

Expected offline result: `Hours found.`

```bash
uv run --group pydantic-ai pytest tests/pydantic_ai_plugin/mcp_test.py
```
