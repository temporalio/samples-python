# MCP Examples

Integration with MCP (Model Context Protocol) servers using OpenAI agents in Temporal workflows.

*Adapted from [OpenAI Agents SDK MCP examples](https://github.com/openai/openai-agents-python/tree/main/examples/mcp)*

Before running these examples, be sure to review the [prerequisites and background on the integration](../README.md).


## Running the Examples

### Stdio MCP

First, start the worker:
```bash
uv run openai_agents/mcp/run_file_system_worker.py
```

Run the workflow:
```bash
uv run openai_agents/mcp/run_file_system_workflow.py
```

This sample assumes that the worker and `run_file_system_workflow.py` are on the same machine.


### MCP v2 with Streamable HTTP

This example uses the MCP v2 API: the worker registers a named server factory
with `OpenAIAgentsPlugin(mcp_servers=...)`, and the workflow creates a durable
proxy with `temporal_mcp_server(...)`.

First, start the MCP server:
```bash
uv run --project openai_agents/mcp/v2 \
  python -m openai_agents.mcp.v2.tools_server
```

Then start the worker:
```bash
uv run --project openai_agents/mcp/v2 \
  python -m openai_agents.mcp.v2.run_worker
```

Finally, run the workflow:
```bash
uv run --project openai_agents/mcp/v2 \
  python -m openai_agents.mcp.v2.run_workflow
```

The separate uv project keeps MCP SDK v2 isolated from samples that still use
the MCP SDK v1 compatibility API.

The remaining examples use the legacy MCP provider API, which is retained for
compatibility.


### Streamable HTTP MCP (Legacy Provider API)

First, start the worker:
```bash
uv run openai_agents/mcp/servers/tools_server.py --transport=streamable-http
```

Then start the worker:
```bash
uv run openai_agents/mcp/run_streamable_http_worker.py
```

Finally, run the workflow:
```bash
uv run openai_agents/mcp/run_streamable_http_workflow.py
```

### SSE MCP

First, start the MCP server:
```bash
uv run openai_agents/mcp/servers/tools_server.py --transport=sse
```

Then start the worker:
```bash
uv run openai_agents/mcp/run_sse_worker.py
```

Finally, run the workflow:
```bash
uv run openai_agents/mcp/run_sse_workflow.py
```

### Prompt Server MCP

First, start the MCP server:
```bash
uv run openai_agents/mcp/servers/prompt_server.py
```

Then start the worker:
```bash
uv run openai_agents/mcp/run_prompt_server_worker.py
```

Finally, run the workflow:
```bash
uv run openai_agents/mcp/run_prompt_server_workflow.py
```


### Memory MCP (Research Scratchpad)

Demonstrates durable note-taking with the Memory MCP server: write seed notes, query by tags, synthesize a brief with citations, then update and delete notes.

Start the worker:
```bash
uv run openai_agents/mcp/run_memory_research_scratchpad_worker.py
```

Run the research scratchpad workflow:
```bash
uv run openai_agents/mcp/run_memory_research_scratchpad_workflow.py
```
