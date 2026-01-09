# Hello World LangGraph Agent

Minimal LangGraph agent with Temporal integration. A single-node graph that processes a query.

## What This Sample Demonstrates

- **Basic plugin setup**: Registering a LangGraph graph with `LangGraphPlugin`
- **Graph registration**: Creating a graph builder function and registering it by name
- **Simple workflow invocation**: Using `compile()` to get a graph runner within a workflow
- **Activity-based node execution**: Each graph node runs as a Temporal activity

## How It Works

1. **State Definition**: A simple `TypedDict` defines the workflow state with `query` and `result` fields
2. **Node Function**: A single node processes the query and returns a result
3. **Graph Builder**: Creates and compiles a minimal StateGraph with one node
4. **Workflow**: Uses `compile("graph_name")` to get a runner and `ainvoke()` to execute
5. **Plugin**: Registers the graph builder so it's available to workflows

## Running the Example

First, start the worker:
```bash
uv run langgraph_plugin/graph_api/hello_world/run_worker.py
```

Then, in a separate terminal, run the workflow:
```bash
uv run langgraph_plugin/graph_api/hello_world/run_workflow.py
```

## Expected Output

```
Result: {'query': 'Hello, Temporal!', 'result': 'Processed: Hello, Temporal!'}
```
