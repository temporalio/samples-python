# Continue-as-New with Task Caching (Functional API)

Demonstrates task result caching across continue-as-new boundaries using the LangGraph Functional API.

## Overview

Long-running workflows may need to use continue-as-new to avoid unbounded event history growth. This sample shows how to preserve task results across continue-as-new boundaries so previously-completed tasks don't re-execute.

## How It Works

1. **Task results are cached** - When a `@task` completes, its result is stored in an in-memory cache
2. **`get_state()` serializes the cache** - Before continue-as-new, call `app.get_state()` to get a checkpoint
3. **`compile(checkpoint=...)` restores the cache** - In the new workflow execution, pass the checkpoint to restore cached results
4. **Cache hits return immediately** - Tasks with matching inputs return cached results without re-execution

## The Pipeline

This sample runs a 5-step pipeline in two phases:

```
Phase 1: step_1 → step_2 → step_3 → [continue-as-new]
Phase 2: step_1* → step_2* → step_3* → step_4 → step_5
         (* = cached, no re-execution)
```

For input value `10`:
- step_1: 10 × 2 = 20
- step_2: 20 + 5 = 25
- step_3: 25 × 3 = 75
- step_4: 75 - 10 = 65
- step_5: 65 + 100 = **165**

## Key Code

### Workflow with Checkpoint

```python
@workflow.defn
class ContinueAsNewWorkflow:
    @workflow.run
    async def run(self, input_data: PipelineInput) -> dict:
        # Restore cache from checkpoint if continuing
        app = compile("pipeline_entrypoint", checkpoint=input_data.checkpoint)

        if input_data.phase == 1:
            # Phase 1: run first 3 tasks
            result = await app.ainvoke({"value": input_data.value, "stop_after": 3})

            # Capture cache state before continue-as-new
            checkpoint = app.get_state()

            workflow.continue_as_new(PipelineInput(
                value=input_data.value,
                checkpoint=checkpoint,  # Pass cached results
                phase=2,
            ))

        # Phase 2: run all 5 (1-3 cached)
        return await app.ainvoke({"value": input_data.value, "stop_after": 5})
```

### Entrypoint with Partial Execution

```python
@entrypoint()
async def pipeline_entrypoint(input_data: dict) -> dict:
    value = input_data["value"]
    stop_after = input_data.get("stop_after", 5)

    result = await step_1(value)
    if stop_after == 1: return {"result": result}

    result = await step_2(result)
    if stop_after == 2: return {"result": result}

    # ... more tasks ...
```

## Running the Sample

1. Start Temporal server:
   ```bash
   temporal server start-dev
   ```

2. Run the worker:
   ```bash
   uv run langgraph_plugin/functional_api/continue_as_new/run_worker.py
   ```

3. Execute the workflow:
   ```bash
   uv run langgraph_plugin/functional_api/continue_as_new/run_workflow.py
   ```

4. **Check the worker logs** - You should see:
   - `step_1`, `step_2`, `step_3` logged once (phase 1)
   - `step_4`, `step_5` logged once (phase 2)
   - No duplicate task execution!

## Files

| File | Description |
|------|-------------|
| `tasks.py` | `@task` functions with logging |
| `entrypoint.py` | `@entrypoint` with stop_after support |
| `workflow.py` | Workflow with continue-as-new logic |
| `run_worker.py` | Worker startup script |
| `run_workflow.py` | Workflow execution script |

## Key Differences from Graph API

| Aspect | Graph API | Functional API |
|--------|-----------|----------------|
| Checkpoint content | Full channel state | Cached task results |
| Resume behavior | Resume mid-graph | Re-execute from start, skip cached tasks |
| Granularity | Node-level | Task-level |

## When to Use

- Long-running pipelines that may hit event history limits
- Workflows with expensive tasks that shouldn't re-execute
- Multi-phase processing where each phase builds on previous results
