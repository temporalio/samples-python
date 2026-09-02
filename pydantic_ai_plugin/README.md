# Pydantic AI Plugin Samples

These samples run ordinary [Pydantic AI](https://ai.pydantic.dev/) agents inside Temporal Workflows with `TemporalDurability`. `PydanticAIPlugin` configures Pydantic payload conversion, the Workflow Sandbox, non-retryable failures, and automatic Activity registration for agents declared on `PydanticAIWorkflow` classes.

The samples use Pydantic AI's credential-free `TestModel` by default. Pass an OpenAI model name in the Workflow input to use a live model instead.

| Sample | What it demonstrates |
| --- | --- |
| [chat](chat) | Multi-turn Updates, durable message history, and Continue-As-New. |
| [tools](tools) | A deterministic in-Workflow tool beside an I/O-style Activity tool. |
| [mcp](mcp) | A stateless in-process FastMCP server whose operations run as Activities. |
| [streaming](streaming) | Pydantic AI events over Temporal Workflow Streams. |
| [human_in_the_loop](human_in_the_loop) | Approval, rejection, and cancellation decisions delivered by Signal. |
| [structured_output](structured_output) | A typed Pydantic model crossing Activity and Workflow boundaries. |
| [multi_agent](multi_agent) | Durable researcher and writer agents coordinated by one Workflow. |
| [logfire](logfire) | Pydantic AI and Temporal tracing wired together by `LogfirePlugin`. |

## Install

```bash
uv sync --group pydantic-ai
temporal server start-dev
```

The dependency group pins `pydantic-ai-slim` to commit `2b45faa97e76461c60500e9755a130b158a2418d`, the head of [pydantic-ai PR #6639](https://github.com/pydantic/pydantic-ai/pull/6639), because the Workflow Streams API used by the streaming sample is not yet released.

## Run

Start a category's Worker, then use the Temporal CLI command in that category's README. With no `model` value, the Workflow uses `TestModel` and needs no API key or network access. For a live run, set `model` to `gateway/openai:gpt-5.2` and export `PYDANTIC_AI_GATEWAY_API_KEY` in the Worker process.

The examples use the declarative registration path: each Workflow subclasses `PydanticAIWorkflow`, lists its agents in `__pydantic_ai_agents__`, and the Client installs `PydanticAIPlugin`. `AgentPlugin(agent)` is the narrower Worker-only alternative when a Workflow class cannot declare its agents; it does not replace the Client-side `PydanticAIPlugin` configuration.

## Unsupported

**Sandboxes:** Pydantic AI does not provide an agent-facing isolation environment whose sessions and shell or filesystem operations are durably managed by this integration.
