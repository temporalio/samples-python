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

## Basic Example

Runs a single workflow that asks OpenAI "What is Temporal?" and returns the response.

```bash
# Terminal 1 — start the worker
python -m langsmith_tracing.basic.worker

# Terminal 2 — run the workflow
python -m langsmith_tracing.basic.starter
```

## Chatbot Example

Starts a long-running workflow that accepts messages via signals and responds via queries. The model has two tools:

- `save_note(name, content)` — saves a note durably (calls an activity)
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

## `add_temporal_runs`

By default, `LangSmithPlugin(add_temporal_runs=False)` only propagates LangSmith context so that `@traceable` and `wrap_openai` calls nest under the correct parent trace.

Set `add_temporal_runs=True` to also create LangSmith runs for each Temporal workflow execution and activity execution, giving you visibility into Temporal operations alongside your LLM calls.

## Viewing Traces

After running either example, open [LangSmith](https://smith.langchain.com/) and look for the project name (`langsmith-basic` or `langsmith-chatbot`).
