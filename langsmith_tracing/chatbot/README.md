# Chatbot with Tool Calls

A long-running conversational workflow with tool calls, signals, and queries. Demonstrates how LangSmith traces an agentic loop where the model calls tools across multiple turns.

See the [parent README](../README.md) for prerequisites.

## Running

```bash
# Terminal 1 — start the worker
python -m langsmith_tracing.chatbot.worker

# Terminal 2 — interactive CLI
python -m langsmith_tracing.chatbot.starter
```

Commands in the CLI:
- Type a message and press Enter to chat
- `exit` — end the session

## Tools

The model has two tools, both implemented as `@traceable` methods on the workflow class:

- **`save_note(name, content)`** — Stores a note in the workflow's in-memory dict. The note is durable because workflow state survives crashes and restarts via Temporal's event history.
- **`read_note(name)`** — Reads a note from the workflow's in-memory dict.

## Trace Structure

### `add_temporal_runs=False` (default)

The chatbot produces two traces: one from the client (starter) and one from the worker. They appear as separate root traces in LangSmith.

```
Chatbot Session a1b2c3d4                      (@traceable, client-side)
├── Turn: What's the capital of Fr..          (@traceable, client-side per-turn)
├── Turn: Save that as a note call..          (@traceable, client-side per-turn)
└── Turn: What did I save about pa..          (@traceable, client-side per-turn)

Session Apr 17 10:30                          (@traceable, workflow)
├── Request: What's the capital of France?    (@traceable, per-message)
│   └── Call OpenAI                           (@traceable, activity)
│       └── openai.responses.create           (automatic via wrap_openai)
├── Request: Save that as a note called paris (@traceable, per-message)
│   ├── Call OpenAI                           (@traceable, activity)
│   │   └── openai.responses.create           → function_call: save_note
│   ├── Save Note                             (@traceable, workflow method)
│   └── Call OpenAI                           (@traceable, activity)
│       └── openai.responses.create           → text response
└── Request: What did I save about paris?     (@traceable, per-message)
    ├── Call OpenAI                           (@traceable, activity)
    │   └── openai.responses.create           → function_call: read_note
    ├── Read Note                             (@traceable, workflow method)
    └── Call OpenAI                           (@traceable, activity)
        └── openai.responses.create           → text response
```

### `add_temporal_runs=True`

With `--add-temporal-runs`, Temporal operation spans wrap each `@traceable` span:

```
Chatbot Session a1b2c3d4                          (@traceable, client-side)
├── Turn: Save that as a note call..              (@traceable, client-side per-turn)
│   └── HandleSignal:user_message                 (automatic, Temporal plugin)
└── ...

RunWorkflow:ChatbotWorkflow                       (automatic, Temporal plugin)
└── Session Apr 17 10:30                          (@traceable, workflow)
    └── Request: Save that as a note called paris (@traceable, per-message)
        ├── ExecuteActivity:call_openai           (automatic, Temporal plugin)
        │   └── Call OpenAI                       (@traceable, activity)
        │       └── openai.responses.create       (automatic via wrap_openai)
        ├── Save Note                             (@traceable, workflow method)
        └── ExecuteActivity:call_openai           (automatic, Temporal plugin)
            └── Call OpenAI                       (@traceable, activity)
                └── openai.responses.create       (automatic via wrap_openai)
```
