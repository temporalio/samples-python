This sample demonstrates how to make MCP calls from a workflow, using the MCP Python SDK. The MCP
server can be a standard `stdio` server, or it can be implemented as a Temporal workflow, giving
rise to durable client sessions. The example uses an MCP server with stateful sessions: the
[sequentialthinking](https://github.com/modelcontextprotocol/servers/tree/main/src/sequentialthinking)
reference MCP server, optionally translated as a Python Temporal workflow.

```
uv sync --group=mcp
uv run mcp_examples/nexus_transport/app.py
```
