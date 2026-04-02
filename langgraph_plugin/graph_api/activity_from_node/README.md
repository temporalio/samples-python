# Activity from Node

Demonstrates calling Temporal activities directly from a LangGraph node using the `run_in_workflow` feature.

## What This Sample Demonstrates

- **run_in_workflow nodes**: Using `temporal_node_metadata(run_in_workflow=True)` to run a node in the workflow context
- **Activity orchestration**: Calling multiple Temporal activities from within a graph node
- **Mixed execution modes**: Combining run_in_workflow nodes with regular activity nodes
- **Sandbox enforcement**: Node code is sandboxed to ensure deterministic execution

## How It Works

1. **Orchestrator Node**: Runs directly in the workflow (not as an activity) with `run_in_workflow=True`
   - Calls `validate_data` activity to validate input
   - Calls `enrich_data` activity to enrich valid data
   - Implements orchestration logic (conditional activity calls)

2. **Finalize Node**: Runs as a regular Temporal activity (default behavior)
   - Processes the enriched data

3. **Activities**: Standard Temporal activities called from the orchestrator
   - `validate_data`: Validates input data
   - `enrich_data`: Enriches data with additional information

## When to Use run_in_workflow

Use `run_in_workflow=True` when your node needs to:
- Call Temporal activities, child workflows, or other Temporal operations
- Use workflow features like timers, signals, or queries
- Implement complex orchestration logic with multiple activity calls

**Important**: Code in run_in_workflow nodes is sandboxed to ensure deterministic execution. Non-deterministic operations (like `random.randint()`) will be blocked.

## Running the Example

First, start the worker:
```bash
uv run langgraph_plugin/graph_api/activity_from_node/run_worker.py
```

Then, in a separate terminal, run the workflow:
```bash
uv run langgraph_plugin/graph_api/activity_from_node/run_workflow.py
```

## Expected Output

```
Result: {'data': 'Hello from LangGraph', 'validated': True, 'enriched_data': 'Hello from LangGraph [enriched at activity]', 'final_result': 'Processed: Hello from LangGraph [enriched at activity]'}
```
