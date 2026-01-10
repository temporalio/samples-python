# Temporal Python Samples

## Serena MCP Server

Always consult Serena memories at the start of a session using `mcp__serena__list_memories` and read relevant ones with `mcp__serena__read_memory`. Save important project-specific learnings to Serena for future sessions.

## Pre-Commit and Pre-Push Checks

**ALWAYS run `poe lint` before committing or pushing** on both repositories:

```bash
# In samples repo (langgraph_plugin)
poe lint

# In SDK repo (sdk-python langgraph-plugin branch)
cd /Users/maxim/temporal/sdk-python-root/langgraph-plugin
poe lint
```

This catches import sorting, formatting, type errors, and other style issues. Never push without confirming lint passes.

## Test Failures

**NEVER delete tests just because they fail.** Failing tests indicate real issues with the implementation that need to be fixed. If tests fail:

1. Investigate the root cause of the failure
2. Fix the implementation, not the tests
3. Only modify tests if they have incorrect assertions or are testing the wrong behavior

Tests are valuable signals - treat failures as bugs to fix, not inconveniences to remove.

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

## Design Decisions

**NEVER jump to implementation when presenting multiple design options.** When you identify several possible approaches to solve a problem:

1. Present all options with their pros and cons
2. Wait for the user to confirm which approach to take
3. Only implement after receiving explicit confirmation

This prevents wasted effort implementing the wrong solution and ensures alignment with user preferences.

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
