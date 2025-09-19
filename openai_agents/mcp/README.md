# MCP Examples

Integration with hosted MCP (Model Context Protocol) servers using OpenAI agents in Temporal workflows.

*Adapted from [OpenAI Agents SDK MCP examples](https://github.com/openai/openai-agents-python/tree/main/examples/mcp)*

Before running these examples, be sure to review the [prerequisites and background on the integration](../README.md).

## MCP Server Dependencies

All examples use self-contained MCP servers in the `servers/` directory. The servers require these dependencies:

```bash
pip install mcp requests
# or
uv add mcp requests
```

## Server Implementations

The `servers/` directory contains self-contained MCP server implementations:

- **`tools_server.py`** - Multi-transport MCP server with tools for arithmetic, weather, and random words. Supports both `--transport=streamable-http` and `--transport=sse`
- **`prompt_server.py`** - MCP server that provides prompts for generating agent instructions (code review example)

## Running the Examples

### File System MCP - Stateless

First, start the worker (supports all MCP workflows):
```bash
uv run openai_agents/mcp/run_file_system_stateless_worker.py
```

Connect to a hosted MCP server for file system operations:
```bash
uv run openai_agents/mcp/run_file_system_stateless_workflow.py
```

This sample assumes that the worker and `run_file_system_workflow.py` are on the same machine.

### File System MCP - Stateful

First, start the worker (supports all MCP workflows):
```bash
uv run openai_agents/mcp/run_file_system_stateful_worker.py
```

Connect to a hosted MCP server for file system operations:
```bash
uv run openai_agents/mcp/run_file_system_stateful_workflow.py
```

### Streamable HTTP MCP - Stateless

First, start the MCP server:
```bash
uv run openai_agents/mcp/servers/tools_server.py --transport=streamable-http
```

Then start the worker:
```bash
uv run openai_agents/mcp/run_streamable_http_stateless_worker.py
```

Finally, run the workflow:
```bash
uv run openai_agents/mcp/run_streamable_http_stateless_workflow.py
```

### SSE MCP - Stateless

First, start the MCP server:
```bash
uv run openai_agents/mcp/servers/tools_server.py --transport=sse
```

Then start the worker:
```bash
uv run openai_agents/mcp/run_sse_stateless_worker.py
```

Finally, run the workflow:
```bash
uv run openai_agents/mcp/run_sse_stateless_workflow.py
```

### Prompt Server MCP - Stateless

First, start the MCP server:
```bash
uv run openai_agents/mcp/servers/prompt_server.py
```

Then start the worker:
```bash
uv run openai_agents/mcp/run_prompt_server_stateless_worker.py
```

Finally, run the workflow:
```bash
uv run openai_agents/mcp/run_prompt_server_stateless_workflow.py
```