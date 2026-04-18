# ReAct Agent (Graph API)

Demonstrates the most common LangGraph pattern: a tool-calling agent that loops between deciding and acting, using conditional edges for routing.

## What This Sample Demonstrates

- Defining a `StateGraph` with an agent->tools loop
- Using `add_conditional_edges` for conditional routing (call tool or finish)
- Accumulating conversation history with `Annotated[list, operator.add]`
- The full ReAct cycle: think -> act -> observe -> repeat

## How It Works

1. The `agent` node examines the conversation history and decides the next action.
2. If a tool is needed, `should_continue` routes to the `tools` node.
3. The `tools` node executes the tool and appends the result to history.
4. Control returns to `agent`, which decides again — loop or finish.
5. When the agent has enough information, `should_continue` routes to `END`.

```
START -> agent -> tools -> agent -> tools -> agent -> END
```

## Running the Sample

Prerequisites: `uv sync --group langgraph` and a running Temporal dev server.

```bash
# Terminal 1
uv run langgraph_plugin/graph_api/react_agent/run_worker.py

# Terminal 2
uv run langgraph_plugin/graph_api/react_agent/run_workflow.py
```

## Files

| File | Description |
|------|-------------|
| `workflow.py` | `AgentState`, node functions, `should_continue` router, graph definition, and `ReactAgentWorkflow` |
| `run_worker.py` | Builds graph, registers with `LangGraphPlugin`, starts worker |
| `run_workflow.py` | Executes the agent workflow and prints the answer |
