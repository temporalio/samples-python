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
| [react_agent](react_agent) | Tool-calling loop showing the explicit per-tool choice: `activity_as_tool` for an existing activity, `tool_as_activity` for an I/O tool, plus an explicit `TemporalModel`. |
| [human_in_the_loop](human_in_the_loop) | Pause on `interrupt_on` and resume via the native LangGraph protocol, mapped to a Temporal Query + Update. |
| [continue_as_new](continue_as_new) | Long-running agent that carries messages and the model/tool result cache across continue-as-new via `run_deep_agent`. |
| [filesystem_backend](filesystem_backend) | Durable real filesystem I/O by wrapping a `FilesystemBackend` in `TemporalBackend`. |
| [subagents](subagents) | Durability propagates across the agent tree — sub-agent model calls become activities with no per-sub-agent wiring. |
| [streaming](streaming) | Stream model chunks to external subscribers via `streaming_topic` + `WorkflowStream`, keeping the durable result identical. |
| [langsmith_tracing](langsmith_tracing) | Compose `DeepAgentsPlugin` with `LangSmithPlugin` for durable execution + LLM tracing. |

## Prerequisites

1. Install dependencies:

   ```bash
   uv sync --group deepagents
   ```

   > The `temporalio-contrib-deepagents` plugin is experimental and not yet
   > published to PyPI, so it is not part of the `deepagents` group above.
   > Until it publishes, install it from a local checkout of the SDK (adjust
   > the path to wherever your `sdk-python` checkout lives):
   >
   > ```bash
   > uv pip install ../sdk-python/temporalio/contrib/deepagents
   > ```
   >
   > The plugin uses a namespace-package overlay layout, so install it
   > non-editable (no `-e`) — an editable install cannot map its sources onto
   > `temporalio.contrib.deepagents`. Once it is on PyPI this step goes away
   > and you can add `temporalio-contrib-deepagents` to the `deepagents` group.

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

> **Use `uv run --no-sync`.** Because the experimental plugin is installed
> out-of-band (`uv pip install …` above) and is not in any dependency group, a
> bare `uv run` or `uv sync` re-syncs the environment to the lockfile first and
> uninstalls it. `--no-sync` runs against the environment as-is. (Once the
> plugin publishes and joins the `deepagents` group, the flag is unnecessary.)

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
  auto-routed, or use `TemporalModel(...)` explicitly.
- **Explicit Workflow-vs-Activity tool choice** — `activity_as_tool`,
  `tool_as_activity`, and `TemporalBackend` move I/O out of workflow code.
- **Human-in-the-loop** — the native LangGraph `interrupt_on` return value
  mapped to a Temporal Query and Update.
- **Long-lived agents** — `run_deep_agent(continue_as_new_after=...)` carries
  messages and the result cache across continue-as-new.
- **Sub-agent durability** — sub-agents inherit the durable model object with no
  extra wiring.
- **Streaming** — forward model chunks to external subscribers while keeping the
  durable result unchanged.
- **Observability** — compose with `LangSmithPlugin` for tracing.

## Related

- [Temporal Deep Agents plugin](https://github.com/temporalio/sdk-python/tree/main/temporalio/contrib/deepagents)
- [LangChain Deep Agents](https://github.com/langchain-ai/deepagents)
- [langgraph_plugin](../langgraph_plugin) — for agents built directly as LangGraph graphs
