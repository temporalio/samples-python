# Microsoft Agent Framework samples

These samples show the [Temporal plugin for Microsoft Agent Framework](https://github.com/temporalio/ai-integrations/tree/main/python/microsoft_agent_framework), which runs an Agent Framework `Agent` inside a Temporal Workflow. You write the agent the way Agent Framework documents it and swap the chat client for `TemporalChatClient`. Each model call then runs as the `microsoft_agent_framework.invoke_model` Activity (`microsoft_agent_framework.invoke_model_streaming` when you stream), with its own timeout and retries. The agent's loop, tools, middleware and approvals run in the Workflow, where Temporal records every step and replays it after a crash or a Worker restart. The docs page is [Microsoft Agent Framework](https://docs.temporal.io/develop/python/integrations/microsoft-agent-framework).

> **Pre-release.** The `temporalio-microsoft-agent-framework` package and its interfaces may change before General Availability.

`MicrosoftAgentFrameworkPlugin` goes on the Client or on the Worker, not both. These samples put it on `Client.connect(...)`; the Worker built from that Client inherits it.

## Samples

| Sample | Description |
|--------|-------------|
| [hello_world](hello_world) | One `Agent` over `TemporalChatClient`, one prompt, one model Activity. Start here. |
| [tools](tools) | A pure `@tool` that runs in the Workflow next to an Activity wrapped with `activity_as_tool`. |
| [mcp](mcp) | Tools from an MCP server through `TemporalMCPToolProvider`; the listing and each call are Activities. Its own uv project, see below. |
| [human_in_the_loop](human_in_the_loop) | A tool with `approval_mode="always_require"`. The Workflow publishes the request through a Query, waits for a `decide` Update and answers on the same session. |
| [middleware](middleware) | Function and chat middleware running in the Workflow: one refuses a tool call, one edits the instructions. |
| [multi_agent](multi_agent) | A coordinator with two sub-agents as tools through `Agent.as_tool()`; every agent's model calls are Activities. |
| [structured_output](structured_output) | `response_format` with a Pydantic model; the Workflow returns the model through the plugin's data converter. |
| [streaming](streaming) | `streaming_topic` publishes each update to a Workflow Stream; the starter prints them as they arrive. |
| [continue_as_new](continue_as_new) | A chat driven by Updates that hands `session.to_dict()` to a fresh run when Temporal suggests Continue-As-New. |
| [open_telemetry](open_telemetry) | `OpenTelemetryPlugin` and `MicrosoftAgentFrameworkPlugin` on one Client: one trace from the starter through the Workflow to the model Activity. |

## Prerequisites

1. Python 3.11 or later. The plugin declares `requires-python = ">=3.11"`, as Temporal Python SDK 1.36 does, so on 3.10 the `microsoft-agent-framework` dependency group resolves to nothing and the tests are not collected.

2. Install the dependencies from the repository root:

   ```bash
   uv sync --group microsoft-agent-framework
   ```

   This installs `temporalio-microsoft-agent-framework`, `agent-framework-openai` and Temporal Python SDK 1.36.0 or later.

3. An OpenAI API key. Each Worker reads it when it builds the `OpenAIChatClient`; the Workflow only carries the model name `gpt-4o-mini`:

   ```bash
   export OPENAI_API_KEY=...
   ```

4. A local Temporal Service from the [Temporal CLI](https://docs.temporal.io/cli):

   ```bash
   temporal server start-dev
   ```

## Running a sample

Each sample has two scripts. Start the Worker first, then the starter in a second terminal, both from the repository root:

```bash
# Terminal 1: start the Worker
uv run microsoft_agent_framework_plugin/<sample>/run_worker.py

# Terminal 2: start the Workflow
uv run microsoft_agent_framework_plugin/<sample>/run_workflow.py
```

For example, for the tools sample:

```bash
# Terminal 1
uv run microsoft_agent_framework_plugin/tools/run_worker.py

# Terminal 2
uv run microsoft_agent_framework_plugin/tools/run_workflow.py
```

The `mcp` sample is its own uv project: the plugin's MCP support needs MCP Python SDK 2, and other samples in this repository still pin SDK 1, so they cannot share one lock file. Run it from its directory:

```bash
cd microsoft_agent_framework_plugin/mcp
uv sync

# Terminal 1
uv run run_worker.py

# Terminal 2
uv run run_workflow.py
```

## Key features

- One Activity per model round trip, `microsoft_agent_framework.invoke_model`, with a 60-second start-to-close timeout in these samples and the plugin's default 10-second heartbeat timeout. Temporal owns retries, so the Workers build the OpenAI client with `AsyncOpenAI(max_retries=0)`.
- Tools run where you put them: a plain `@tool` runs in the Workflow, `activity_as_tool` runs an Activity with its own `start_to_close_timeout`.
- MCP servers are registered on the Worker. `TemporalMCPToolProvider` lists and calls their tools through the `temporalio.mcp.<server>.list-tools` and `temporalio.mcp.<server>.call-tool` Activities.
- Approvals are Agent Framework's own `approval_mode`; the wait is a Workflow Update with a validator.
- Middleware and context providers run in the Workflow, so they must be deterministic; I/O in middleware goes through `workflow.execute_activity`.
- Streaming publishes `ChatResponseUpdate` dicts to a Workflow Stream topic, batched every 100 milliseconds.
- Long chats carry `session.to_dict()` across Continue-As-New and restore it with `AgentSession.from_dict`.
- `OpenTelemetryPlugin` composes on the same Client; `create_tracer_provider()` keeps the spans Agent Framework starts from Workflow code replay-safe.

## Tests

The tests run every sample against the plugin's scripted `FakeChatClient` and a local dev server, with no API key:

```bash
uv run poe test tests/microsoft_agent_framework_plugin
uv run poe test tests/microsoft_agent_framework_plugin --workflow-environment time-skipping
cd microsoft_agent_framework_plugin/mcp && uv run poe test
```

## Related

- [Temporal plugin for Microsoft Agent Framework](https://github.com/temporalio/ai-integrations/tree/main/python/microsoft_agent_framework)
- [Microsoft Agent Framework](https://github.com/microsoft/agent-framework)
- [Microsoft Agent Framework docs page](https://docs.temporal.io/develop/python/integrations/microsoft-agent-framework)
