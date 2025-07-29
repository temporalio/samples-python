# Hosted MCP Examples

Integration with hosted MCP (Model Context Protocol) servers using OpenAI agents in Temporal workflows.

*Adapted from [OpenAI Agents SDK hosted_mcp examples](https://github.com/openai/openai-agents-python/tree/main/examples/hosted_mcp)*

Before running these examples, be sure to review the [prerequisites and background on the integration](../README.md).

## Running the Examples

First, start the worker (supports all MCP workflows):
```bash
uv run openai_agents/hosted_mcp/run_worker.py
```

Then run individual examples in separate terminals:

### Simple MCP Connection
Connect to a hosted MCP server without approval requirements (trusted servers):
```bash
uv run openai_agents/hosted_mcp/run_simple_mcp_workflow.py
```

### MCP with Approval Callbacks
Connect to a hosted MCP server with approval workflow for tool execution:
```bash
uv run openai_agents/hosted_mcp/run_approval_mcp_workflow.py
```

## MCP Server Configuration

Both examples default to using the GitMCP server (`https://gitmcp.io/openai/codex`) which provides repository analysis capabilities. The workflows can be easily modified to use different MCP servers by changing the `server_url` parameter.

### Approval Workflow Notes

The approval example demonstrates the callback structure for tool approvals in a Temporal context. In this implementation:

- The approval callback automatically approves requests for demonstration purposes
- In production environments, approvals would typically be handled by communicating with a human user. Because the approval executes in the Temporal workflow, you can use signals or updates to communicate approval status.
