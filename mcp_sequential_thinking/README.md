This sample demonstrates an approach to writing an AI agent workflow that uses the [sequentialthinking](https://github.com/modelcontextprotocol/servers/tree/main/src/sequentialthinking) MCP server example.

- The agent is a Temporal workflow (a durable agent)
- The sequential thinking MCP server is stateful, and hence is also implemented as a Temporal workflow (a durable MCP server)
- The durable agent communicates with the durable MCP server via nexus (could also be done via activities, but nexus exists for this purpose)

## Setup

```
temporal operator nexus endpoint create \
  --target-namespace default \
  --name mcp-sequential-thinking-nexus-endpoint \
  --target-task-queue mcp-sequential-thinking-task-queue
```

In one terminal, run the Temporal worker in the handler namespace:
```
uv run mcp_sequential_thinking/worker.py
```

In another terminal, start the caller workflow:
```
uv run mcp_sequential_thinking/app.py
```
