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

# or

uv run mcp_sequential_thinking/app_transport.py
```

## Integration Approaches

This sample includes two approaches for MCP integration:

### 1. Nexus Client Approach

Uses a custom client (`nexus_client.py`) that bypasses anyio dependencies and routes MCP operations directly through Nexus. This approach:
- Maps MCP operations directly to Nexus calls
- Avoids complex async stream coordination
- Simple, reliable, and production-ready

### 2. Transport-Based Approach

Uses the standard MCP ClientSession with a custom Nexus transport (`nexus_transport.py`). This approach:
- Demonstrates that anyio can work in Temporal workflows with a small patch to the event loop class used by the SDK
- Uses the full MCP SDK ClientSession
- More complex due to bidirectional stream requirements

## Notes

### anyio Compatibility

The MCP Python SDK uses anyio internally, which is incompatible with the current Python SDK workflow implementation:

1. anyio checks for Python 3.12+'s eager task factory feature
2. Temporal's workflow event loop implements `get_task_factory()` but raises `NotImplementedError`
3. Standard asyncio returns `None` when no task factory is set

The solution (`event_loop_patch.py`) catches the `NotImplementedError` and returns `None`, allowing anyio to fall back to normal task creation.

### Session Management

MCP sessions map naturally to Temporal workflow instances:
- The `initialize()` call starts the workflow session
- Each session maintains stateful context (thoughts, branches)
- The workflow instance ID serves as the session identifier

## Files

- `agent_workflow_nexus_client.py` - Agent using the Nexus client approach
- `agent_workflow_nexus_transport.py` - Agent using the transport approach
- `nexus_client.py` - Custom MCP client that routes through Nexus
- `nexus_transport.py` - MCP transport implementation for Nexus
- `event_loop_patch.py` - Temporal event loop compatibility fix
- `mcp_server/workflow.py` - Stateful MCP server workflow
- `mcp_server/nexus_service.py` - Nexus service interface

## Testing

Run the tests with:
```
uv run pytest tests/mcp_sequential_thinking/
```