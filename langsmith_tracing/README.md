# LangSmith Tracing

This sample demonstrates [LangSmith](https://smith.langchain.com/) tracing integration with Temporal workflows using the `LangSmithPlugin`.

Two examples are included:

- **basic/** — A one-shot LLM workflow that sends a prompt to OpenAI and returns the response.
- **chatbot/** — A long-running conversational workflow with tool calls (save/read notes), signals, and queries.

## Prerequisites

Install dependencies:

```bash
uv sync --group langsmith-tracing
```

Set environment variables:

```bash
export OPENAI_API_KEY="sk-..."
export LANGSMITH_API_KEY="lsv2_..."
export LANGCHAIN_TRACING_V2=true
```

A local Temporal server must be running (`temporal server start-dev`).

## Three Layers of Tracing

This sample shows three complementary ways LangSmith captures trace data:

1. **Automatic (`wrap_openai`)** — Wrapping the OpenAI client with `wrap_openai()` automatically captures model parameters, token usage, and latency for every LLM call. No extra code needed.

2. **Explicit (`@traceable`)** — Decorating functions with `@traceable` creates named spans for your business logic. You control the name, tags, metadata, and `run_type` (chain, llm, tool, retriever). This is how you structure traces to tell a story about what your application is doing.

3. **Temporal (`add_temporal_runs=True`)** — The `LangSmithPlugin` can optionally create LangSmith runs for each Temporal workflow execution and activity execution, giving visibility into the orchestration layer alongside your LLM calls.

## Basic Example

Runs a single workflow that asks OpenAI "What is Temporal?" and returns the response.

```bash
# Terminal 1 — start the worker
python -m langsmith_tracing.basic.worker

# Terminal 2 — run the workflow
python -m langsmith_tracing.basic.starter
```

### Trace output (`add_temporal_runs=False`, default)

```
Basic LLM Request                    (@traceable, client-side)
└── Ask: What is Temporal?           (@traceable, workflow)
    └── Call OpenAI                   (@traceable, activity)
        └── openai.responses.create   (automatic via wrap_openai)
```

### Trace output (`add_temporal_runs=True`)

Pass `--temporal-runs` to both the worker and starter:

```bash
python -m langsmith_tracing.basic.worker --temporal-runs
python -m langsmith_tracing.basic.starter --temporal-runs
```

```
Basic LLM Request                    (@traceable, client-side)
└── StartWorkflow:BasicLLMWorkflow    (automatic, Temporal plugin)
    └── RunWorkflow:BasicLLMWorkflow  (automatic, Temporal plugin)
        └── Ask: What is Temporal?    (@traceable, workflow)
            └── ExecuteActivity:call_openai  (automatic, Temporal plugin)
                └── Call OpenAI       (@traceable, activity)
                    └── openai.responses.create  (automatic via wrap_openai)
```

## Chatbot Example

Starts a long-running workflow that accepts messages via signals and responds via queries. The model has two tools:

- `save_note(name, content)` — saves a note durably via an activity
- `read_note(name)` — reads a note from workflow state (no activity needed)

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

### Trace output (conversation with tool calls)

```
Chatbot Session a1b2c3d4              (@traceable, client-side)
├── Turn: What's the capital of Fr..  (@traceable, client-side)
├── Turn: Save that as a note call..  (@traceable, client-side)
└── Turn: What did I save about pa..  (@traceable, client-side)
```

On the worker side:

```
Session Apr 17 10:30                          (@traceable, workflow)
├── Request: What's the capital of France?    (@traceable, workflow)
│   └── Call OpenAI                           (@traceable + wrap_openai, activity)
├── Request: Save that as a note called paris (@traceable, workflow)
│   ├── Call OpenAI                           → returns function_call: save_note
│   ├── Save Note                             (@traceable, activity)
│   └── Call OpenAI                           → returns text response
└── Request: What did I save about paris?     (@traceable, workflow)
    ├── Call OpenAI                           → returns function_call: read_note
    └── Call OpenAI                           → returns text (read_note is a workflow state lookup, no activity)
```

## Viewing Traces

After running either example, open [LangSmith](https://smith.langchain.com/) and look for the project name (`langsmith-basic` or `langsmith-chatbot`).
