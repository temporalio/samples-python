# OpenRouter

These samples call [OpenRouter](https://openrouter.ai/) from Temporal Activities. OpenRouter serves hundreds of models from many providers behind one OpenAI-compatible API and one API key, and picks providers and models per request. Temporal handles everything around those calls: retries with backoff, fan-out with bounded concurrency, crash recovery, pausing for a human, and a durable per-attempt record of what was called and what it cost.

| Sample | Description |
|--------|-------------|
| [prompt_batch](prompt_batch) | Fan one OpenRouter call out per prompt with OpenRouter's Auto Router, and collect answer, model, and cost per prompt. Shows Temporal-owned retries, `Retry-After` handling, and retries served for free from OpenRouter's response cache. Start here. |
| [budget_gate](budget_gate) | The same batch, but it pauses instead of failing when money runs out, whether a soft budget in the Workflow or OpenRouter refusing the call for lack of credits, and resumes on a `raise_budget` Update. |

For OpenRouter as the model provider behind the [OpenAI Agents SDK plugin](../openai_agents), see [openai_agents/model_providers](../openai_agents/model_providers#openrouter).

## Prerequisites

1. Follow the [repository prerequisites](../README.md), then install this sample's dependencies:

   ```bash
   uv sync --group openrouter
   ```

2. Start a local dev server with the [Temporal CLI](https://docs.temporal.io/cli):

   ```bash
   temporal server start-dev
   ```

3. Set an [OpenRouter API key](https://openrouter.ai/settings/keys) in the Worker's environment. A few cents of credit is enough for these samples.

   ```bash
   export OPENROUTER_API_KEY="sk-or-v1-..."
   ```

   Optional: set `OPENROUTER_HTTP_REFERER` and `OPENROUTER_APP_TITLE` for [app attribution](https://openrouter.ai/docs/app-attribution) in OpenRouter's rankings.

The API key stays in the Worker process. Prompts, answers, models, and costs go through the Workflow and are recorded in Event History; the key never does.

## Running a sample

Each sample has a Worker and a starter. Run them in separate terminals:

```bash
# Terminal 1
uv run --group openrouter openrouter/prompt_batch/run_worker.py

# Terminal 2
uv run --group openrouter openrouter/prompt_batch/run_workflow.py "Explain retries in one sentence." "Write a haiku about databases."
```

## How the Activity calls OpenRouter

[activities.py](activities.py) uses the `openai` SDK pointed at `https://openrouter.ai/api/v1`, which is the setup OpenRouter documents for OpenAI-compatible clients. OpenRouter-specific fields go in `extra_body`. Four things matter for durable execution:

- **Temporal owns retries.** The client is created with `max_retries=0`, so every attempt is one HTTP call and shows up in Event History. If you use OpenRouter's official `openrouter` package instead, pass `retry_config=RetryConfig("none", ...)`: by default it retries 5xx and connection errors for up to an hour, invisibly.
- **Errors are classified.** 408, 429, and 5xx raise a retryable `ApplicationError`; 400, 401, 403 (moderation or permissions), and other 4xx raise a non-retryable one. Running out of money gets its own type, `OpenRouterOutOfCredits`: OpenRouter returns 402 when the account has no credits and 403 `Key limit exceeded` when the API key hit its own credit limit. A `Retry-After` header becomes the next retry delay. OpenRouter can also return HTTP 200 with an `error` body and no `choices`; the Activity checks for that.
- **Retries are free when the first call succeeded.** The Activity sends `X-OpenRouter-Cache: true`, so if a Worker dies after OpenRouter answered but before Temporal recorded the result, the retried, byte-identical request is served from OpenRouter's response cache and billed at $0. Nothing per-attempt goes in the request body, so attempts stay identical.
- **Heartbeats.** The Activity heartbeats so a dead Worker is detected after `heartbeat_timeout` (10s) rather than after the full `start_to_close_timeout`.

Each result carries the concrete model OpenRouter chose, OpenRouter's reported `usage.cost`, the generation id, and the cache status.

## What Temporal does and does not guarantee

Activities are at-least-once. If a Worker dies mid-call, the retry re-sends the request; within the cache TTL that retry costs nothing, but two identical requests in flight at the same time both miss the cache and both bill. Completed Activities are never re-run, so a restarted batch resumes at the first unfinished prompt.

OpenRouter decides which provider and model serve a request, in milliseconds (Auto Router, `models` fallback lists, provider preferences). Temporal decides what happens over time: waiting out a rate limit, surviving a Worker crash, pausing for hours until a human acts, and keeping the audit trail.

## Batch size

Each Activity adds a few events to the Workflow's Event History, and every answer is part of the Workflow result. These samples cap a batch at 100 prompts. For larger batches, use one Workflow per slice, or the pattern in [batch_sliding_window](../batch_sliding_window) with continue-as-new.

## Tests

The tests replace OpenRouter with a fake HTTP transport and the Activity with a fake, so they need no API key and make no network calls:

```bash
uv run --group openrouter pytest tests/openrouter
```
