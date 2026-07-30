# Human-in-the-loop (Hook-based)

The canonical Strands HITL pattern. A `BeforeToolCallEvent` hook gates a sensitive tool behind human approval by calling `event.interrupt(...)`. The agent stops with `stop_reason == "interrupt"`; the workflow waits on a Temporal signal for the response, then resumes with `InterruptResponseContent`.

## What This Sample Demonstrates

- Using `HookProvider` + `BeforeToolCallEvent` to interrupt before a tool runs
- Pairing Strands' interrupt machinery with Temporal signals + queries
- Resuming the agent with `[{"interruptResponse": ...}]` content

## Running the Sample

```bash
# Terminal 1
uv run strands_plugin/human_in_the_loop/run_worker.py

# Terminal 2
uv run strands_plugin/human_in_the_loop/run_workflow.py
```

The starter script queries the workflow until an approval is pending, prints the reason, then signals `"approve"`. To exercise the denial path, change the signal to anything other than `"approve"`.

## Files

| File | Description |
|------|-------------|
| `workflow.py` | `delete_file` tool, `ApprovalHook`, `HumanInTheLoopWorkflow` |
| `run_worker.py` | Registers `StrandsPlugin`, starts the worker |
| `run_workflow.py` | Starts the workflow, polls for the approval, sends the signal |
