# Claude Agent SDK Samples

⚠️ **Pre-release**: this integration and its interfaces may change before General Availability.

These samples demonstrate the [Temporal Claude Agent SDK integration](https://github.com/temporalio/ai-integrations/tree/main/python/claude_agent_sdk), which runs [Claude Code](https://code.claude.com/docs/en/agent-sdk/overview) agents as Temporal Workflows. You write ordinary Claude Agent SDK code in a Workflow, and Claude Code runs unmodified. If a Worker fails, the agent picks up where it left off, and approvals, hooks, and custom tools run as durable Workflow code.

## Samples

| Category | Sample | What it shows |
| --- | --- | --- |
| Agent Chat | [agent_chat](agent_chat) | A multi-turn chat driven by Updates, with Continue-As-New that resumes Claude's session in the next run. Start here. |
| Tools | [tools](tools) | One custom tool computed in the Workflow and one that runs an Activity, both via `@tool` and `create_sdk_mcp_server`. |
| Streaming | [streaming](streaming) | Token-by-token output through a Workflow Stream, with or without a subscriber. |
| Human in the Loop | [human_in_the_loop](human_in_the_loop) | `can_use_tool` waits durably for a person's Update: approve, deny, or cancel. |
| Structured Output | [structured_output](structured_output) | A JSON-schema result validated as a Pydantic model at the Workflow boundary. |
| Multi-Agent | [multi_agent](multi_agent) | Claude Code's native subagents: a coordinator delegating to a researcher and a writer. |
| Plugin with Custom Transport | [plugin_with_custom_transport](plugin_with_custom_transport) | A Claude Code plugin with a skill and an MCP server, copied into a Docker Sandbox (`sbx`) by a custom connector that runs Claude Code there. |

Observability is not covered yet. OpenTelemetry context propagation into Claude Code is planned, with a sample to follow.

Most samples run Claude Code as a subprocess of the Worker. `plugin_with_custom_transport` runs it in a Docker Sandbox instead.

## Prerequisites

Install the [Temporal CLI](https://docs.temporal.io/cli), then the dependencies:

```bash
uv sync --group claude-agent-sdk
```

The `claude-agent-sdk` package bundles Claude Code, so you don't need to install it separately. Each sample's README has the commands to run it.

## Tests

The tests run every sample against the scripted API and a local dev server, with no credentials or Docker:

```bash
uv run --group claude-agent-sdk pytest tests/claude_agent_sdk_plugin
```

They're skipped on Windows, where the default transport's shell scripts don't run.
