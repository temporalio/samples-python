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
- `notes` — display all saved notes
- `exit` — end the session

## Tools

The model has two tools:

- **`save_note(name, content)`** — Saves a note durably via a Temporal activity. The workflow stores the note in its state dict and calls the activity, which creates a visible trace span in LangSmith.
- **`read_note(name)`** — Reads a note via a Temporal activity. The workflow looks up the note from its state dict and passes it to the activity for tracing visibility.

## Trace Structure

### Client-side traces

```
Chatbot Session a1b2c3d4              (@traceable, client-side)
├── Turn: What's the capital of Fr..  (@traceable, client-side per-turn)
├── Turn: Save that as a note call..  (@traceable, client-side per-turn)
└── Turn: What did I save about pa..  (@traceable, client-side per-turn)
```

<!-- TODO: Add screenshot of client-side LangSmith trace showing session with nested turns -->

### Worker-side traces (`add_temporal_runs=False`)

```
Session Apr 17 10:30                          (@traceable, workflow)
├── Request: What's the capital of France?    (@traceable, per-message)
│   └── Call OpenAI                           (@traceable, activity)
│       └── openai.responses.create           (automatic via wrap_openai)
├── Request: Save that as a note called paris (@traceable, per-message)
│   ├── Call OpenAI                           (@traceable, activity)
│   │   └── openai.responses.create           → function_call: save_note
│   ├── Save Note                             (@traceable, activity)
│   └── Call OpenAI                           (@traceable, activity)
│       └── openai.responses.create           → text response
└── Request: What did I save about paris?     (@traceable, per-message)
    ├── Call OpenAI                           (@traceable, activity)
    │   └── openai.responses.create           → function_call: read_note
    ├── Read Note                             (@traceable, activity)
    └── Call OpenAI                           (@traceable, activity)
        └── openai.responses.create           → text response
```

<!-- TODO: Add screenshot of worker-side trace showing the tool call loop with save_note and read_note -->

### Worker-side traces (`add_temporal_runs=True`)

With `--temporal-runs`, Temporal operation spans wrap each `@traceable` span:

```
RunWorkflow:ChatbotWorkflow                       (automatic, Temporal plugin)
└── Session Apr 17 10:30                          (@traceable, workflow)
    └── Request: Save that as a note called paris (@traceable, per-message)
        ├── ExecuteActivity:call_openai           (automatic, Temporal plugin)
        │   └── Call OpenAI                       (@traceable, activity)
        │       └── openai.responses.create       (automatic via wrap_openai)
        ├── ExecuteActivity:save_note             (automatic, Temporal plugin)
        │   └── Save Note                         (@traceable, activity)
        └── ExecuteActivity:call_openai           (automatic, Temporal plugin)
            └── Call OpenAI                       (@traceable, activity)
                └── openai.responses.create       (automatic via wrap_openai)
```

<!-- TODO: Add screenshot of worker-side trace with add_temporal_runs=True showing Temporal spans wrapping the tool loop -->
