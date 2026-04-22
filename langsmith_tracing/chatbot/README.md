# Chatbot with Tool Calls

A long-running conversational workflow with tool calls and update handlers. Demonstrates how LangSmith traces an agentic loop where the model calls tools across multiple turns.

See the [parent README](../README.md) for prerequisites.

## Running

```bash
# Terminal 1 — start the worker
uv run --group langsmith-tracing python -m langsmith_tracing.chatbot.worker

# Terminal 2 — interactive CLI
uv run --group langsmith-tracing python -m langsmith_tracing.chatbot.starter
```

Commands in the CLI:
- Type a message and press Enter to chat
- `exit` — end the session

## Tools

The model has two tools, both implemented as `@traceable` methods on the workflow class:

- **`save_note(name, content)`** — Stores a note in the workflow's in-memory dict. The note is durable because workflow state survives crashes and restarts via Temporal's event history.
- **`read_note(name)`** — Reads a note from the workflow's in-memory dict.

## Architecture

The main `@workflow.run` method runs a loop that processes user messages (calls `_query_openai`, which handles the tool-call loop). The `message_from_user` update handler coordinates: it hands the message to the main loop via a shared `_pending_message` field, then waits for the response.

This means:
- Activity calls and the tool loop happen inside the main workflow run
- The update handler's trace just shows the input/output of the coordination step

## Trace Structure

### `add_temporal_runs=False` (default)

Only `@traceable` and `wrap_openai` spans appear. The client-side `@traceable` wraps `start_workflow` and each `execute_update`, so both workflow and update traces nest under it via context propagation.

```
Chatbot Session a1b2c3d4              (@traceable, client-side)
├── Session Apr 17 10:30               (@traceable, workflow main loop)
│   ├── Request: hello                 (@traceable, per-message in main loop)
│   │   └── Call OpenAI                (@traceable, activity)
│   │       └── ChatOpenAI             (automatic via wrap_openai)
│   └── Request: save that as note 15  (@traceable, per-message in main loop)
│       ├── Call OpenAI                → function_call: save_note
│       ├── Save Note                  (@traceable, workflow method)
│       └── Call OpenAI                → text response
├── Update: hello                      (@traceable, update handler)
└── Update: save that as note 15       (@traceable, update handler)
```

### `add_temporal_runs=True`

With `--add-temporal-runs`, Temporal operation spans are added. `StartWorkflow`/`RunWorkflow` and `StartActivity`/`RunActivity` appear as sibling pairs.

```
Chatbot Session a1b2c3d4                          (@traceable, client-side)
├── StartWorkflow:ChatbotWorkflow                 (automatic, Temporal plugin)
├── RunWorkflow:ChatbotWorkflow                   (automatic, Temporal plugin)
│   └── Session Apr 17 10:30                      (@traceable, workflow main loop)
│       └── Request: save that as note 15         (@traceable, per-message)
│           ├── StartActivity:call_openai         (automatic, Temporal plugin)
│           ├── RunActivity:call_openai           (automatic, Temporal plugin)
│           │   └── Call OpenAI                   (@traceable, activity)
│           │       └── ChatOpenAI                (automatic via wrap_openai)
│           ├── Save Note                         (@traceable, workflow method)
│           ├── StartActivity:call_openai         (automatic, Temporal plugin)
│           └── RunActivity:call_openai           (automatic, Temporal plugin)
│               └── Call OpenAI                   (@traceable, activity)
│                   └── ChatOpenAI                (automatic via wrap_openai)
├── StartWorkflowUpdate:message_from_user         (automatic, Temporal plugin)
│   └── HandleUpdate:message_from_user            (automatic, Temporal plugin)
│       └── Update: save that as note 15          (@traceable, update handler)
└── ...
```

Note that the `Request:` chain (with activity calls) lives under `RunWorkflow` (the main loop), while the `Update:` span lives under `HandleUpdate` (the update handler). They're connected by the shared workflow state but appear as separate subtrees.
