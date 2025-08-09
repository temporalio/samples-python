```
uv sync --group=mcp
```

Use the MCP SDK client with a custom Nexus transport to make an MCP call from workflow code:

```bash
uv run mcp_examples/nexus_transport/app.py
```

To test the MCP call without using a workflow set `WITHOUT_WORKFLOW=1`
```bash
WITHOUT_WORKFLOW=1 uv run mcp_examples/nexus_transport/app.py
```

