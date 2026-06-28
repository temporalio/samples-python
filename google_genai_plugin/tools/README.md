# Tools

Two tool surfaces wired into one Gemini `generate_content` call, both driven by
the SDK's automatic function-calling (AFC) loop:

| Pattern | When to use it |
|---------|----------------|
| `@activity.defn` wrapped via `activity_as_tool` | Anything with I/O or non-determinism — runs as a durable activity. |
| Plain workflow method | Pure, deterministic logic — runs in-workflow with no activity dispatch. |

A single prompt exercises both: the model calls `get_weather` (an activity),
then `recommend_activity` (a workflow method).

## What This Sample Demonstrates

- `activity_as_tool` carrying per-tool `ActivityConfig` (timeouts, retries)
- Passing a plain workflow method as a tool alongside an activity-backed one
- The AFC loop running inside the workflow, dispatching tool calls durably

## Running the Sample

Prerequisites: install dependencies, set `GOOGLE_API_KEY`, and start a Temporal
dev server. See the [suite README](../README.md).

```bash
# Terminal 1
uv run google_genai_plugin/tools/run_worker.py

# Terminal 2
uv run google_genai_plugin/tools/run_workflow.py
```

## Files

| File | Description |
|------|-------------|
| `workflow.py` | `get_weather` activity, `recommend_activity` method, and `ToolsWorkflow` |
| `run_worker.py` | Registers `GoogleGenAIPlugin` + the `get_weather` activity |
| `run_workflow.py` | Executes the workflow and prints the result |
