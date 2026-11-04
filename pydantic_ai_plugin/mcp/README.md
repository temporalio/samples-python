# MCP

The agent starts a stateless MCP server in a separate stdio process. `MCPToolset` exposes its `support_hours` tool, while `TemporalDurability` moves MCP listing and tool calls into Temporal Activities. The server keeps no session state, so Activity retries are safe.

```bash
uv run --project pydantic_ai_plugin pydantic_ai_plugin/mcp/run_worker.py
temporal workflow execute --type MCPWorkflow --task-queue pydantic-ai-mcp --workflow-id pydantic-ai-mcp-1 --input '{"prompt":"When is support staffed?","model":null}'
```

Use `"model":"gateway/openai:gpt-5.2"` for a live run.

Expected offline result: `Hours found.`

```bash
uv run --project pydantic_ai_plugin pytest pydantic_ai_plugin/tests/mcp_test.py
```
