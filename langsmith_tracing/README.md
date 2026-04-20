# LangSmith Tracing

This sample demonstrates [LangSmith](https://smith.langchain.com/) tracing integration with Temporal workflows using the [`LangSmithPlugin`](https://python.temporal.io/temporalio.contrib.langsmith.html).

Two examples are included:

- **[basic/](basic/)** — A one-shot LLM workflow that sends a prompt to OpenAI and returns the response.
- **[chatbot/](chatbot/)** — A long-running conversational workflow with tool calls (save/read notes), signals, and queries.

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

1. **Automatic (`wrap_openai`)** — Wrapping the OpenAI client with `wrap_openai()` automatically creates a child span for every LLM call, capturing model parameters, token usage, and latency. No extra code needed.

2. **Explicit (`@traceable`)** — Decorating functions with `@traceable` creates named spans for your business logic. You control the name, tags, metadata, and `run_type` (chain, llm, tool, retriever). This is how you structure traces to tell a story about what your application is doing.

3. **Temporal (`add_temporal_runs=True`)** — The `LangSmithPlugin` can optionally create LangSmith runs for each Temporal workflow execution and activity execution, giving visibility into the orchestration layer alongside your LLM calls.

## `add_temporal_runs`

By default, `LangSmithPlugin(add_temporal_runs=False)` only propagates LangSmith context so that `@traceable` and `wrap_openai` calls nest correctly.

Set `add_temporal_runs=True` to also create LangSmith runs for Temporal operations (workflow executions, activity executions, signals, etc.), giving full visibility into the orchestration layer. Both examples support a `--add-temporal-runs` CLI flag to toggle this.

## Further Reading

- [LangSmith documentation](https://docs.smith.langchain.com/)
- [Temporal Python SDK LangSmith plugin](https://python.temporal.io/temporalio.contrib.langsmith.html)
- [LangSmith `@traceable` guide](https://docs.smith.langchain.com/observability/how-to/annotate-code)
- [LangSmith `wrap_openai` guide](https://docs.smith.langchain.com/observability/how-to/trace-with-openai)
