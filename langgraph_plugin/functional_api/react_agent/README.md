# ReAct Agent (Functional API)

Same agent pattern as the Graph API version, but using a `while` loop instead of conditional edges — making the control flow explicit.

## What This Sample Demonstrates

- The ReAct loop as a natural `while True` loop in Python
- `@task` functions for agent thinking and tool execution
- How the Functional API makes agent loops readable and extensible

## How It Works

1. The `agent_think` task examines the query and tool history, deciding the next action.
2. If a tool is needed, `execute_tool` runs it and the result is appended to history.
3. The loop continues until `agent_think` returns a final answer.

```python
while True:
    decision = await agent_think(query, history)
    if decision["action"] == "final":
        return decision["answer"]
    result = await execute_tool(decision["tool_name"], decision["tool_input"])
    history.append(result)
```

## Running the Sample

Prerequisites: `uv sync --group langgraph` and a running Temporal dev server.

```bash
# Terminal 1
uv run langgraph_plugin/functional_api/react_agent/run_worker.py

# Terminal 2
uv run langgraph_plugin/functional_api/react_agent/run_workflow.py
```

## Files

| File | Description |
|------|-------------|
| `workflow.py` | `@task` functions (agent_think, execute_tool), `@entrypoint`, and `ReactAgentFunctionalWorkflow` |
| `run_worker.py` | Registers tasks and entrypoint with `LangGraphPlugin`, starts worker |
| `run_workflow.py` | Executes the agent workflow and prints the answer |
