# Hello World (Functional API)

A minimal example demonstrating the LangGraph Functional API with Temporal integration.

## Overview

This sample shows the basic pattern for using `@task` and `@entrypoint` decorators with Temporal:

1. **`@task`** - Defines a function that runs as a Temporal activity
2. **`@entrypoint`** - Orchestrates tasks, runs in the Temporal workflow

## Key Concepts

### Task as Activity

```python
@task
def process_query(query: str) -> str:
    """This runs as a Temporal activity with automatic retries."""
    return f"Processed: {query}"
```

### Entrypoint as Orchestrator

```python
@entrypoint()
async def hello_world_entrypoint(query: str) -> dict:
    # Use await to call tasks (required for Temporal)
    result = await process_query(query)
    return {"query": query, "result": result}
```

### Workflow Wrapper

```python
@workflow.defn
class HelloWorldWorkflow:
    @workflow.run
    async def run(self, query: str) -> dict:
        app = compile("hello_world")
        return await app.ainvoke(query)
```

## Running the Sample

1. Start Temporal server:
   ```bash
   temporal server start-dev
   ```

2. Run the worker:
   ```bash
   uv run langgraph_plugin/functional_api/hello_world/run_worker.py
   ```

3. Execute the workflow:
   ```bash
   uv run langgraph_plugin/functional_api/hello_world/run_workflow.py
   ```

## Files

| File | Description |
|------|-------------|
| `tasks.py` | `@task` function definitions |
| `entrypoint.py` | `@entrypoint` orchestration logic |
| `workflow.py` | Temporal workflow wrapper |
| `run_worker.py` | Worker startup script |
| `run_workflow.py` | Workflow execution script |

## Adapting from Standard LangGraph

```python
# Standard LangGraph
result = my_task(input).result()  # Blocking

# Temporal-compatible
result = await my_task(input)  # Async await
```

See the main README for the complete migration guide.
