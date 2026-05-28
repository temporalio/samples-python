# Activity Interrupt

A `@activity.defn`-wrapped tool raises `InterruptException(Interrupt(...))` directly. The plugin's failure converter preserves the `Interrupt` payload across the activity boundary, so the agent stops with `stop_reason == "interrupt"` just like in the hook-based [human_in_the_loop](../human_in_the_loop) sample.

When to reach for this style instead of a hook:

- The decision to pause depends on data that's only visible inside the activity (a permissions service, a row in a database, etc.).
- You don't want to load that data into workflow context just to make the call.

## What This Sample Demonstrates

- Raising `InterruptException` from a Temporal activity tool
- The plugin's failure converter carrying `Interrupt` across the activity boundary
- Why `StrandsPlugin` must be attached to the **client** (not just the worker)

## Running the Sample

```bash
# Terminal 1
uv run strands_plugin/activity_interrupt/run_worker.py

# Terminal 2
uv run strands_plugin/activity_interrupt/run_workflow.py
```

The starter requests deletion of a "protected" resource. The `delete_thing` activity raises an interrupt for protected names; the starter signals `"approve"` to release it.

## Files

| File | Description |
|------|-------------|
| `workflow.py` | `delete_thing` activity that raises `InterruptException`, plus the workflow that handles resumption |
| `run_worker.py` | `StrandsPlugin` on the client + worker, registers the activity |
| `run_workflow.py` | Starts the workflow and signals approval |
