# Continue-as-new

A chat-style workflow accumulates history with every turn and will eventually hit Temporal's per-workflow history limit. `workflow.info().is_continue_as_new_suggested()` flips `True` once the server decides history has grown large enough; this sample checks it after each turn and hands off to a fresh run with `agent.messages` as input.

## What This Sample Demonstrates

- Driving a multi-turn chat with **updates**, so each caller gets the assistant's reply back from the same call
- Seeding a new `TemporalAgent` with prior `agent.messages`
- Using `workflow.info().is_continue_as_new_suggested()` + `workflow.continue_as_new(...)` to keep the workflow alive indefinitely
- Draining in-flight update handlers with `workflow.all_handlers_finished` before continue-as-new

## Running the Sample

```bash
# Terminal 1
uv run strands_plugin/continue_as_new/run_worker.py

# Terminal 2
uv run strands_plugin/continue_as_new/run_workflow.py
```

The starter calls the `turn` update for each user message and prints the assistant's reply, then signals `end_chat`. In a real chatbot, a UI would drive the updates and the workflow would run indefinitely, continuing-as-new whenever history gets large.

## Files

| File | Description |
|------|-------------|
| `workflow.py` | `ChatInput`, `ChatWorkflow` with `turn` update, `end_chat` signal, and `messages` query |
| `run_worker.py` | Registers `StrandsPlugin`, starts the worker |
| `run_workflow.py` | Starts the chat, sends a few turns, ends it |
