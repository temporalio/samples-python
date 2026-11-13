# Continue-as-new

A chat that runs as long as you like. Each user turn is an Update, so the caller gets the reply from the same call. History grows with every turn, and `workflow.info().is_continue_as_new_suggested()` turns `True` once the Temporal Service decides it is large enough. The Workflow waits on that or on the `end_chat` Signal, lets in-flight Updates finish with `workflow.all_handlers_finished`, and hands `session.to_dict()` to a fresh run, which restores it with `AgentSession.from_dict`.

What crosses the boundary: the serialized session, which holds the transcript, any pending approval state and the provider's conversation id. What does not: the `Agent` object, provider connections and spans; the new run builds the agent again.

## What this sample demonstrates

- The `turn` Update, the `end_chat` Signal and the `transcript` Query
- An `asyncio.Lock` so turns take the session one at a time
- `workflow.continue_as_new(ChatInput(session=session.to_dict()))`

## Running the sample

```bash
# Terminal 1
uv run microsoft_agent_framework_plugin/continue_as_new/run_worker.py

# Terminal 2
uv run microsoft_agent_framework_plugin/continue_as_new/run_workflow.py
```

The starter sends two turns, prints each reply, prints the number of messages in the session and ends the chat. Two turns do not reach the default threshold, so the Workflow `microsoft-agent-framework-chat` completes in one run; the test lowers the threshold to see the handoff. In a chat application a UI would drive the Updates and the Workflow would run on, continuing as new whenever history gets large.

## Files

| File | Description |
|------|-------------|
| `workflow.py` | `ChatInput` and `ChatWorkflow` with the Update, Signal and Query |
| `run_worker.py` | Registers the plugin, starts the Worker on `microsoft-agent-framework-chat` |
| `run_workflow.py` | Starts the chat, sends two turns, ends it |
