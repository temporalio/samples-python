# Temporal Google ADK Integration

⚠️ **Experimental** — This integration is experimental and its interfaces may
change prior to General Availability.

This directory contains samples demonstrating how to run
[Google ADK](https://google.github.io/adk-docs/) agents durably inside Temporal
workflows using `temporalio.contrib.google_adk_agents`. Each scenario is a
self-contained subdirectory with its own worker, workflow starter, workflow and
activity packages, and README.

## Overview

The integration combines:

- **Temporal workflows** for durable orchestration of agent control flow
- **Google ADK** for agent creation, model calls, tools, and MCP integration

`GoogleAdkPlugin` configures a Pydantic payload converter, sandbox passthrough
for `google.adk` / `google.genai` / `mcp`, a deterministic ADK runtime, and the
model activities. `TemporalModel` runs each LLM call as an activity, so every
model turn is durable and observable.

## Prerequisites

- Temporal server [running locally](https://docs.temporal.io/cli/server#start-dev)
- Dependencies installed via `uv sync --group google-adk`
- Google API key set as an environment variable:
  `export GOOGLE_API_KEY=your_key_here`

All scenarios default to the `gemini-2.5-flash` model. ADK also supports other
providers (for example, non-Gemini models via LiteLLM); swap the model name on
`TemporalModel` to use one.

## Scenarios

Each directory contains a complete example with its own README:

| Scenario | What it shows |
| --- | --- |
| [basic](./basic/README.md) | A single ADK agent with `TemporalModel` and one model call — no tools. The minimal end-to-end example. |
| [tools](./tools/README.md) | A Temporal activity wrapped as an ADK tool with `activity_tool`, so tool calls run as their own activities. |
| [agent_patterns](./agent_patterns/README.md) | A coordinator `LlmAgent` with `sub_agents`, each a `TemporalModel` with a per-agent activity summary. |
| [mcp](./mcp/README.md) | A local echo MCP toolset via `TemporalMcpToolSet` / `TemporalMcpToolSetProvider`, running MCP tools as activities. Self-contained, no Node required. |
| [streaming](./streaming/README.md) | Token streaming via `TemporalModel(streaming_topic=...)` + `WorkflowStream`, consumed by a starter with `WorkflowStreamClient`. |

To run any scenario, start its worker in one terminal and its workflow starter
in another:

```bash
uv run python -m google_adk_agents.<scenario>.run_worker
uv run python -m google_adk_agents.<scenario>.run_<name>_workflow
```
