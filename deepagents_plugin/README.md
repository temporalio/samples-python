# Deep Agents Samples

These samples demonstrate the [Temporal Deep Agents plugin](https://github.com/temporalio/sdk-python/tree/main/temporalio/contrib/deepagents),
which makes [LangChain Deep Agents](https://github.com/langchain-ai/deepagents)
durable. Build your agent with `create_deep_agent(...)` inside a
`@workflow.defn` and add `DeepAgentsPlugin()` to your client — each LLM call and
each I/O tool/backend operation becomes a Temporal Activity, while the agent's
control loop runs (and deterministically replays) inside the Workflow.

> **Experimental.** The `temporalio.contrib.deepagents` plugin is experimental
> and its API may change.

`DeepAgentsPlugin` is a **client-level** plugin: add it to `Client.connect(...)`
and the SDK propagates it to any Worker built from that client. Add it on exactly
one side.

## Samples

| Sample | Description |
|--------|-------------|
| [hello_world](hello_world) | Minimal single-shot Deep Agent; a bare `model=` string auto-routed through the model activity. Start here. |
| [react_agent](react_agent) | Tool-calling loop showing the explicit per-tool choice: `activity_as_tool` for an existing activity, `tool_as_activity` for an I/O tool, plus per-agent `activity_options` via `create_temporal_deep_agent`. |
| [human_in_the_loop](human_in_the_loop) | Pause on `interrupt_on` and resume via the native LangGraph protocol, mapped to a Temporal Query + Update. |
| [continue_as_new](continue_as_new) | Long-running agent that carries messages and the model/tool result cache across continue-as-new via `run_deep_agent`. |
| [filesystem_backend](filesystem_backend) | Durable real filesystem I/O by wrapping a `FilesystemBackend` in `TemporalBackend`. |
| [subagents](subagents) | Durability propagates across the agent tree — sub-agent model calls become activities with no per-sub-agent wiring. |
| [streaming](streaming) | Stream model chunks to external subscribers via `streaming_topic` + `WorkflowStream`, keeping the durable result identical. |
| [langsmith_tracing](langsmith_tracing) | Compose `DeepAgentsPlugin` with `LangSmithPlugin` for durable execution + LLM tracing. |

## Prerequisites

> **Python ≥ 3.11 required.** `deepagents` (and therefore the plugin) does not
> support older interpreters. On Python 3.10 the `deepagents` dependency group
> resolves to nothing, so `uv sync` silently installs none of the dependencies
> below.

1. Install dependencies:

   ```bash
   uv sync --group deepagents
   ```

   > The Deep Agents plugin ships as the `temporalio[deepagents]` extra. It
   > is merged to `sdk-python` `main` but the current PyPI release (1.31.0)
   > predates the merge and does not carry the extra, so the `deepagents`
   > group above does not include it yet. Until a release ships the extra
   > (> 1.31.0), install it from main:
   >
   > ```bash
   > uv pip install "temporalio[deepagents] @ git+https://github.com/temporalio/sdk-python.git"
   > ```
   >
   > This builds the SDK from source (including its Rust core), so expect a
   > few minutes on first install. Once a release with the extra is on PyPI
   > this step goes away: `temporalio[deepagents]` joins the `deepagents`
   > group and a plain `uv sync --group deepagents` is all you need.

2. Configure a model provider. The samples use
   `anthropic:claude-sonnet-4-5`, which needs an Anthropic API key:

   ```bash
   export ANTHROPIC_API_KEY=...
   ```

   To use a different provider, change the `model=` string in the sample's
   `workflow.py` and set that provider's credentials (the plugin resolves the
   model worker-side via LangChain's `init_chat_model`).

3. Start a [Temporal dev server](https://docs.temporal.io/cli#start-dev-server):

   ```bash
   temporal server start-dev
   ```

## Running a Sample

> **Use `uv run --no-sync`.** Because the plugin is installed out-of-band
> from sdk-python main (see Prerequisites) and is not yet in any dependency
> group, a bare `uv run` or `uv sync` re-syncs the environment to the lockfile
> first and uninstalls it. `--no-sync` runs against the environment as-is.
> (Once a released `temporalio[deepagents]` joins the `deepagents` group, the
> flag becomes unnecessary.)

Most samples have two scripts. Start the Worker first, then the Workflow starter
in a separate terminal:

```bash
# Terminal 1: start the Worker
uv run --no-sync deepagents_plugin/<sample>/run_worker.py

# Terminal 2: start the Workflow
uv run --no-sync deepagents_plugin/<sample>/run_workflow.py
```

For example, to run the hello world sample:

```bash
# Terminal 1
uv run --no-sync deepagents_plugin/hello_world/run_worker.py

# Terminal 2
uv run --no-sync deepagents_plugin/hello_world/run_workflow.py
```

The `langsmith_tracing` sample instead bundles the worker and starter into a
single driver:

```bash
uv run --no-sync deepagents_plugin/langsmith_tracing/main.py
```

## Key Features Demonstrated

- **Durable model invocation** — every LLM call runs in an `invoke_model`
  activity with configurable timeouts and retries; a bare `model=` string is
  auto-routed, or use `create_temporal_deep_agent(..., activity_options=...)`
  to scope model-call options per agent (recommended).
- **Explicit Workflow-vs-Activity tool choice** — `activity_as_tool`,
  `tool_as_activity`, and `TemporalBackend` move I/O out of workflow code.
- **Human-in-the-loop** — the native LangGraph `interrupt_on` return value
  mapped to a Temporal Query and Update.
- **Long-lived agents** — `run_deep_agent(...)` carries messages and the result
  cache across server-suggested (or explicitly thresholded) continue-as-new.
- **Sub-agent durability** — sub-agents inherit the durable model object with no
  extra wiring.
- **Streaming** — forward model chunks to external subscribers while keeping the
  durable result unchanged.
- **Observability** — compose with `LangSmithPlugin` for tracing.

## Related

- [Temporal Deep Agents plugin](https://github.com/temporalio/sdk-python/tree/main/temporalio/contrib/deepagents)
- [LangChain Deep Agents](https://github.com/langchain-ai/deepagents)
- [langgraph_plugin](../langgraph_plugin) — for agents built directly as LangGraph graphs
