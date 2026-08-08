# LiteLLM Activity

This sample calls an LLM provider through [LiteLLM](https://docs.litellm.ai/) from a Temporal Activity.

LLM calls perform network I/O and return nondeterministic results, so they must not run in Workflow code. The Workflow only schedules the Activity and records its result, keeping replay deterministic.

## Prerequisites

Follow the [repository prerequisites](../README.md), then install the sample's dependencies:

```bash
uv sync --group litellm
```

Set the API key expected by your provider. This example uses OpenAI by default:

```bash
export OPENAI_API_KEY="your-api-key"
```

To use another [LiteLLM-supported provider](https://docs.litellm.ai/docs/providers), set its credentials and model name. For example:

```bash
export ANTHROPIC_API_KEY="your-api-key"
export LITELLM_MODEL="anthropic/claude-sonnet-4-5-20250929"
```

Provider credentials stay in the Worker environment; they are not passed through the Workflow or stored in Event History.

## Run the sample

Start a local Temporal server, then run these commands in separate terminals:

```bash
# Terminal 1: run the Worker
uv run --group litellm litellm_activity/worker.py

# Terminal 2: start a Workflow
uv run --group litellm litellm_activity/starter.py \
  "Why should LLM calls run in Temporal Activities?"
```

The Activity gives each provider call a 30-second client timeout. The Workflow gives each Activity attempt 45 seconds, limits the entire Activity execution to two minutes, and retries failures for up to three total attempts with exponential backoff. LiteLLM's own retries are disabled so Temporal records and controls every attempt.

## Tests

The tests replace the provider call and Activity with deterministic fakes, so they do not require an API key or make live LLM requests:

```bash
uv run --group litellm pytest tests/litellm_activity
```
