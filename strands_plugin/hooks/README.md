# Hooks

Strands' [hook system](https://strandsagents.com/) lets you subscribe callbacks to lifecycle events (`BeforeToolCallEvent`, `AfterToolCallEvent`, `BeforeModelCallEvent`, etc.). With the Temporal plugin, hook callbacks run in workflow context — so they must be deterministic — but you can dispatch I/O via `activity_as_hook`.

This sample wires two callbacks to `AfterToolCallEvent`:

1. An **in-workflow** callback that appends to per-workflow state. Pure data, deterministic across replay.
2. An **activity-backed** callback (`activity_as_hook(persist_tool_call, ...)`) that calls a Temporal activity for the actual audit write. The `activity_input=` selector pulls a serializable value out of the event.

## What This Sample Demonstrates

- Subscribing multiple callbacks to one hook event
- Mixing deterministic in-workflow callbacks with off-workflow activity callbacks
- The `activity_input=` selector for `activity_as_hook`

## Running the Sample

```bash
# Terminal 1
uv run strands_plugin/hooks/run_worker.py

# Terminal 2
uv run strands_plugin/hooks/run_workflow.py
```

The Temporal UI will show one `invoke_model` activity per agent turn plus a `persist_tool_call` activity per tool call.

## Files

| File | Description |
|------|-------------|
| `workflow.py` | `echo` tool, `AuditHook` (in-workflow + activity-backed), `HooksWorkflow` |
| `run_worker.py` | Registers `StrandsPlugin` + `persist_tool_call`, starts worker |
| `run_workflow.py` | Executes the workflow and prints the list of fired events |
