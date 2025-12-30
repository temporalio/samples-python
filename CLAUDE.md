# Temporal Python Samples

## Serena MCP Server

Always consult Serena memories at the start of a session using `mcp__serena__list_memories` and read relevant ones with `mcp__serena__read_memory`. Save important project-specific learnings to Serena for future sessions.

## Client Initialization Pattern

Use the `ClientConfig` pattern for client initialization to support environment-based configuration:

```python
from temporalio.client import Client
from temporalio.envconfig import ClientConfig

config = ClientConfig.load_client_connect_config()
config.setdefault("target_host", "localhost:7233")
client = await Client.connect(**config)
```

This pattern allows configuration via environment variables while providing sensible defaults.

## LangGraph Guidelines

### Agent Creation

- **DO NOT** use `create_react_agent` from `langgraph.prebuilt` - it is deprecated
- **USE** `create_agent` from `langchain.agents` instead

```python
# Wrong (deprecated)
from langgraph.prebuilt import create_react_agent
agent = create_react_agent(model=model, tools=[...], prompt="...")

# Correct
from langchain.agents import create_agent
agent = create_agent(model=model, tools=[...], system_prompt="...")
```
