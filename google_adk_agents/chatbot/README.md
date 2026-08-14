# Chatbot — Multi-Turn Conversation via Updates

A no-frills conversational chatbot: an ADK `Agent` whose
`model=TemporalModel("gemini-2.5-flash")`, driven by an `InMemoryRunner` inside a
workflow that stays alive across turns. Unlike the [basic](../basic/README.md)
single-shot sample, one ADK session persists for the life of the workflow, so
the assistant remembers earlier turns.

Each conversational turn arrives as a Temporal **Update**: the `message` update
handler feeds the user's text into `runner.run_async` on the persisted session
and returns the assistant's reply as the update result. The handler has a noop
validator that accepts every message. Every model turn still runs as its own
`invoke_model` activity.

Before running, review the [prerequisites in the suite README](../README.md)
(Temporal dev server, `uv sync --group google-adk`, and
`export GOOGLE_API_KEY=...`).

## Running

Start the worker in one terminal:

```bash
uv run google_adk_agents/chatbot/run_worker.py
```

Then start the interactive client in another terminal:

```bash
uv run google_adk_agents/chatbot/run_chatbot_workflow.py
```

## What to expect

The client starts the workflow, then reads messages from stdin. Each line is
sent as an update and the assistant's reply is printed. Enter an empty line or
`/quit` to end the session, which terminates the workflow.

## In the Temporal UI

Open the workflow `google-adk-agents-chatbot-workflow-id`. In the history you
will see the workflow stay running to accept updates, with one `invoke_model`
activity per turn. The workflow itself stays deterministic and replay-safe.
