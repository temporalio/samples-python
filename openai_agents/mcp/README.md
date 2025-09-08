# Hosted MCP Examples

Integration with hosted MCP (Model Context Protocol) servers using OpenAI agents in Temporal workflows.

*Adapted from [OpenAI Agents SDK MCP examples](https://github.com/openai/openai-agents-python/tree/main/examples/mcp)*

Before running these examples, be sure to review the [prerequisites and background on the integration](../README.md).

## Running the Examples

### File System MCP

First, start the worker (supports all MCP workflows):
```bash
uv run openai_agents/mcp/run_file_system_worker.py
```

Connect to a hosted MCP server for file system operations:
```bash
uv run openai_agents/mcp/run_file_system_workflow.py
```

This sample assumes that the worker and `run_file_system_workflow.py` are on the same machine.