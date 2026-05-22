# Strands Agents Samples

These samples demonstrate the [Temporal Strands plugin](https://github.com/temporalio/sdk-python/tree/main/temporalio/contrib/strands), which runs [Strands Agents](https://strandsagents.com/) inside Temporal Workflows. Model invocations, tool calls, and MCP tool calls all execute as Temporal Activities, so you get durable execution, Temporal-managed retries, and timeouts.

## Samples

| Sample | Description |
|--------|-------------|
| [hello_world](hello_world) | Minimal `TemporalAgent` invocation. Start here. |
| [tools](tools) | Three tool patterns side by side: in-workflow `@tool`, custom `@activity.defn` wrapped via `activity_as_tool`, and a `strands_tools` tool wrapped as a Temporal activity. |
| [human_in_the_loop](human_in_the_loop) | Pause a tool call on `BeforeToolCallEvent.interrupt()`, resume via Temporal signal. The canonical Strands HITL pattern. |
| [tool_interrupt](tool_interrupt) | Raise `InterruptException` from a Temporal activity to surface a HITL prompt across the activity boundary. Plugin-specific feature. |
| [hooks](hooks) | `HookProvider` with both an in-workflow callback and an `activity_as_hook` callback for I/O. |
| [mcp](mcp) | Connect to an MCP server (`FastMCP` echo) via `TemporalMCPClient`. |
| [structured_output](structured_output) | Pydantic-typed agent output via `structured_output_model`. |
| [streaming](streaming) | Forward model chunks to an external subscriber via `streaming_topic` + `WorkflowStream`. |
| [continue_as_new](continue_as_new) | Chat-style workflow that hands off `agent.messages` when history grows large. |

## Prerequisites

1. Install dependencies:

   ```bash
   uv sync --group strands
   ```

   > The `strands` extra of `temporalio` is shipping in an upcoming release. Until then, install the SDK from the strands branch:
   >
   > ```bash
   > uv pip install -e ../sdk-python --extra strands-agents --extra pydantic
   > ```

2. Configure AWS credentials. The samples use the plugin's default `BedrockModel()`, which picks up the standard AWS SDK credential chain. Make sure the credentials grant access to a Bedrock model in your selected region (e.g., `us-west-2`).

   ```bash
   export AWS_REGION=us-west-2
   # plus AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY or an SSO profile
   ```

   You can pick a specific model by passing it to `BedrockModel(model_id="...")` in each sample's worker.

3. Start a [Temporal dev server](https://docs.temporal.io/cli#start-dev-server):

   ```bash
   temporal server start-dev
   ```

## Running a Sample

Each sample has two scripts. Start the Worker first, then the Workflow starter in a separate terminal:

```bash
# Terminal 1: start the Worker
uv run strands_plugin/<sample>/run_worker.py

# Terminal 2: start the Workflow
uv run strands_plugin/<sample>/run_workflow.py
```

For example, to run the tools sample:

```bash
# Terminal 1
uv run strands_plugin/tools/run_worker.py

# Terminal 2
uv run strands_plugin/tools/run_workflow.py
```

## Key Features Demonstrated

- **Durable model invocation** — every model call runs in an `invoke_model` activity with configurable timeouts and retries.
- **Three ways to define tools** — pure Strands `@tool`, custom Temporal activities, and ecosystem `strands_tools` wrapped as activities.
- **Human-in-the-loop** — both hook-based (`BeforeToolCallEvent.interrupt()`) and tool-body (`raise InterruptException`) styles.
- **Hook system** — deterministic in-workflow callbacks plus I/O callbacks dispatched via `activity_as_hook`.
- **MCP integration** — connect to MCP servers at worker startup; tool calls dispatched through per-server activities.
- **Structured output** — Pydantic-typed agent results via the plugin's `pydantic_data_converter`.
- **Streaming** — forward model chunks live to external subscribers.
- **Long-lived chats** — hand off `agent.messages` via `continue-as-new` to stay under Temporal's history limit.

## Related

- [Temporal Strands plugin docs](https://github.com/temporalio/sdk-python/tree/main/temporalio/contrib/strands)
- [Strands Agents](https://strandsagents.com/)
