### Use MCP SDK in a workflow

Check the MCP tool call works without using a workflow
```bash
WITHOUT_WORKFLOW=1 uv run mcp_examples/use_mcp_sdk_in_workflow.py
```

Use the MCP SDK client from a workflow with a custom Nexus transport:
```bash
uv run mcp_examples/use_mcp_sdk_in_workflow.py
```