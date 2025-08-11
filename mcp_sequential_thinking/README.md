# Temporal MCP Sequential Thinking Example

This example demonstrates how to implement a durable MCP (Model Context Protocol) server using Temporal workflows that maintains state for complex, branching thought processes.

- The agent is a Temporal workflow (a durable agent)
- The sequential thinking MCP server is stateful, and hence is also implemented as a Temporal workflow (a durable MCP server)
- The durable agent communicates with the durable MCP server via nexus

## Setup

```
temporal operator nexus endpoint create \
  --target-namespace default \
  --name mcp-sequential-thinking-nexus-endpoint \
  --target-task-queue mcp-sequential-thinking-task-queue

uv run mcp_sequential_thinking/worker.py

uv run mcp_sequential_thinking/app.py
```
