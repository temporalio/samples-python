# Chat

A multi-turn conversation using `client.chats`. The chat session carries history
across turns, and each `send_message` call runs as a durable Temporal activity.

## What This Sample Demonstrates

- Creating a chat session with `client.chats.create(...)`
- Sending multiple turns with `await chat.send_message(...)`
- Conversation state persisting across durable activity calls

## Running the Sample

Prerequisites: install dependencies, set `GOOGLE_API_KEY`, and start a Temporal
dev server. See the [suite README](../README.md).

```bash
# Terminal 1
uv run google_genai_plugin/chat/run_worker.py

# Terminal 2
uv run google_genai_plugin/chat/run_workflow.py
```

## Files

| File | Description |
|------|-------------|
| `workflow.py` | `ChatWorkflow` — sends a list of prompts over one chat session |
| `run_worker.py` | Registers `GoogleGenAIPlugin`, starts the worker |
| `run_workflow.py` | Executes the workflow and prints each turn's reply |
