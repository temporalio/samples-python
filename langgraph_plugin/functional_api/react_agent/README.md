# ReAct Agent (Functional API)

A ReAct (Reasoning and Acting) agent that uses tools to answer questions, implemented with the Functional API.

## Overview

The ReAct pattern alternates between:
1. **Think** - LLM decides what action to take
2. **Act** - Execute the chosen tool
3. **Observe** - Feed tool results back to LLM
4. **Repeat** - Until the LLM has enough information to answer

## Architecture

```
User Query
    │
    ▼
┌─────────────┐
│ call_model  │ ◄──────────────┐
│   (task)    │                │
└─────┬───────┘                │
      │                        │
      ▼                        │
  Has tool calls?              │
      │                        │
  YES │     NO                 │
      │      └──► Return Answer
      ▼                        │
┌─────────────┐                │
│execute_tools│                │
│   (task)    │ ───────────────┘
└─────────────┘
```

Each box is a `@task` that runs as a Temporal activity.

## Key Code

### Entrypoint Logic

```python
@entrypoint()
async def react_agent_entrypoint(query: str, max_iterations: int = 10) -> dict:
    messages = [{"role": "user", "content": query}]

    for iteration in range(max_iterations):
        # Think: Call LLM
        response = await call_model(messages)
        messages.append(response)

        # Check if done
        if not response.get("tool_calls"):
            return {"final_answer": response["content"]}

        # Act: Execute tools
        tool_results = await execute_tools(response["tool_calls"])
        messages.extend(tool_results)

    return {"final_answer": "Max iterations reached"}
```

### Tasks

```python
@task
def call_model(messages: list) -> dict:
    """LLM call with tool definitions - runs as activity."""
    return llm.invoke(messages)

@task
def execute_tools(tool_calls: list) -> list:
    """Execute requested tools - runs as activity."""
    return [execute_tool(tc) for tc in tool_calls]
```

## Why Temporal?

- **Durability**: Long reasoning chains complete reliably
- **Retries**: API failures are handled automatically
- **Visibility**: Each think/act step visible in UI
- **Timeouts**: Control LLM call durations

## Running the Sample

1. Start Temporal:
   ```bash
   temporal server start-dev
   ```

2. Set your API key and run the worker:
   ```bash
   export OPENAI_API_KEY=your-key
   uv run langgraph_plugin/functional_api/react_agent/run_worker.py
   ```

3. Execute a query:
   ```bash
   uv run langgraph_plugin/functional_api/react_agent/run_workflow.py
   ```

## Comparison with Graph API

| Aspect | Graph API | Functional API |
|--------|-----------|----------------|
| Control flow | Conditional edges | Python loop |
| State | Shared TypedDict | Local variables |
| Readability | Graph visualization | Linear code |
