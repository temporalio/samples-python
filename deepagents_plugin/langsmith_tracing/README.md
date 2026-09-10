# LangSmith Tracing

Run a Deep Agent durably **and** trace its LLM calls to
[LangSmith](https://smith.langchain.com/), by composing `LangSmithPlugin`
alongside `DeepAgentsPlugin`. The plugin carries no tracing context of its own;
the observability plugin captures the model calls that `DeepAgentsPlugin` runs as
activities. Registration order of the two plugins does not matter.

Following the shipped tracing samples, this scenario bundles the worker and
starter into a single `main.py` and has no automated test (it requires external
API keys).

## What This Sample Demonstrates

- Composing `DeepAgentsPlugin` with `temporalio.contrib.langsmith.LangSmithPlugin`
- Order-independent plugin registration

## Running the Sample

Prerequisites: Python >= 3.11 with the [suite setup](../README.md#prerequisites)
applied, a running Temporal dev server
(`temporal server start-dev`), and these environment variables:

```bash
export ANTHROPIC_API_KEY=...
export LANGSMITH_API_KEY=...   # or LANGCHAIN_API_KEY
export LANGSMITH_TRACING=true
```

Then run the single-process driver:

```bash
uv run deepagents_plugin/langsmith_tracing/main.py
```

Traces appear in your LangSmith project.

## Files

| File | Description |
|------|-------------|
| `workflow.py` | `TracedAgent`: an ordinary Deep Agent |
| `main.py` | Composes `LangSmithPlugin` + `DeepAgentsPlugin`, runs the workflow once |
