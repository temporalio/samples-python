# Tools

Three Strands tool patterns wired into one `TemporalAgent`:

| Pattern | When to use it |
|---------|----------------|
| `@tool` from `strands` | Pure, deterministic logic with no I/O. Runs in workflow context. |
| `@activity.defn` wrapped via `activity_as_tool` | Anything with I/O, non-determinism, or significant runtime — gets durable retries and timeouts. |
| `strands_tools.<tool>` wrapped in an `@activity.defn` | Reuse Strands ecosystem tools (`shell`, `current_time`, `python_repl`, …) while keeping workflow code deterministic. |

A single prompt exercises all three. The resulting Temporal history shows an `invoke_model` for each model turn, plus `fetch_weather` and `shell` activity calls; the `letter_counter` call runs in-workflow and doesn't show up as an activity.

## What This Sample Demonstrates

- Three coexisting tool surfaces on one agent
- `workflow.activity_as_tool` carrying per-tool activity options (timeouts)
- Wrapping `strands_tools` tools so their I/O happens in an activity

## Running the Sample

```bash
# Terminal 1
uv run strands_plugin/tools/run_worker.py

# Terminal 2
uv run strands_plugin/tools/run_workflow.py
```

## Files

| File | Description |
|------|-------------|
| `workflow.py` | The three tools, the `TemporalAgent`, and `ToolsWorkflow` |
| `run_worker.py` | Registers `StrandsPlugin` + the two activities, starts the worker |
| `run_workflow.py` | Executes the workflow and prints the result |
