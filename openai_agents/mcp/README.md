# MCP Examples

Integration with MCP (Model Context Protocol) servers using OpenAI agents in Temporal workflows.

*Adapted from [OpenAI Agents SDK MCP examples](https://github.com/openai/openai-agents-python/tree/main/examples/mcp)*

Before running these examples, be sure to review the [prerequisites and background on the integration](../README.md).


## Running the Examples

### File System MCP - Stateless

First, start the worker:
```bash
uv run openai_agents/mcp/run_file_system_stateless_worker.py
```

Run the workflow:
```bash
uv run openai_agents/mcp/run_file_system_stateless_workflow.py
```

This sample assumes that the worker and `run_file_system_workflow.py` are on the same machine.

### File System MCP - Stateful

First, start the worker:
```bash
uv run openai_agents/mcp/run_file_system_stateful_worker.py
```

Run the workflow:
```bash
uv run openai_agents/mcp/run_file_system_stateful_workflow.py
```

### Streamable HTTP MCP - Stateless

First, start the worker:
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