# Continue-as-New with Graph API

This sample demonstrates how to use Temporal's continue-as-new feature with LangGraph's Graph API. The key design principle is that **the graph is completely unaware of Temporal or continue-as-new** - all checkpoint logic is handled by the workflow.

## Overview

The sample includes:

- **`graph.py`**: A pure 5-step linear graph that knows nothing about Temporal
- **`workflow.py`**: A workflow that uses `should_continue` callback to control execution and implements continue-as-new

## How It Works

### The Pure Graph

The graph is a simple linear pipeline:

```
START -> step_1 -> step_2 -> step_3 -> step_4 -> step_5 -> END
```

Each step adds a result to the state. The graph has NO knowledge of:
- Temporal
- Continue-as-new
- Checkpointing

### The Workflow

The workflow controls when to stop and checkpoint using the `should_continue` callback:

```python
def should_continue() -> bool:
    nonlocal steps_executed
    steps_executed += 1
    return steps_executed <= input.steps_per_execution
```

When `should_continue()` returns `False`, the graph execution stops and returns a checkpoint containing:
- Current state values
- Next nodes to execute
- Completed nodes list
- Cached writes for trigger injection

The workflow then calls `continue_as_new()` with this checkpoint to resume in a new execution.

### Execution Flow

With `steps_per_execution=2`, the 5-step graph requires 3 workflow executions:

1. **Execution 1**: Runs step_1, step_2 → continue-as-new
2. **Execution 2**: Runs step_3, step_4 → continue-as-new
3. **Execution 3**: Runs step_5 → completes

## Running the Sample

1. Start the Temporal server:
   ```bash
   temporal server start-dev
   ```

2. In one terminal, start the worker:
   ```bash
   cd samples-python
   uv run python -m langgraph_plugin.graph_api.continue_as_new.run_worker
   ```

3. In another terminal, run the workflow:
   ```bash
   cd samples-python
   uv run python -m langgraph_plugin.graph_api.continue_as_new.run_workflow
   ```

## Expected Output

The workflow will output:
```
Pipeline completed!
Results: ['step_1: initialized', 'step_2: processed', 'step_3: transformed', 'step_4: validated', 'step_5: finalized']
```

In the Temporal UI, you'll see the workflow has multiple runs connected by continue-as-new.

## Key Concepts

### `should_continue` Callback

The `should_continue` callback is passed to `ainvoke()` and is called after each step (tick) of the graph:

```python
result = await app.ainvoke(input_state, should_continue=should_continue)
```

When it returns `False`, execution stops and the result contains `CHECKPOINT_KEY` with state snapshot.

### Checkpoint Contents

The checkpoint (`StateSnapshot`) contains:
- `values`: Current state values
- `next`: Tuple of next node names to execute
- `metadata`: Step counter, completed nodes, cached writes
- `tasks`: Empty for should_continue stops (used for interrupt resume)

### Restoring from Checkpoint

When creating a runner with a checkpoint, the runner:
1. Restores completed nodes list
2. Caches writes from last executed nodes
3. On resume, injects cached writes to trigger next nodes
4. Skips re-executing completed nodes

## Comparison with Functional API

| Aspect | Graph API | Functional API |
|--------|-----------|----------------|
| Checkpoint content | Full graph state + writes | Task result cache |
| Resume mechanism | Trigger injection | Cache lookup |
| Graph changes | Supports continue mid-graph | Re-executes from start |
