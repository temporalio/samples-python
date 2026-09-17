# Prompt batch

Fan one OpenRouter call out per prompt and collect the answers.

## What this sample demonstrates

- One Activity per prompt, run concurrently under a semaphore, so a slow or failing prompt never blocks the others.
- OpenRouter's Auto Router (`openrouter/auto`) choosing a model per prompt, with the chosen model and OpenRouter's reported cost returned for each.
- Temporal-owned retries: 429 and 5xx retry with backoff and honor `Retry-After`; 4xx errors fail fast and the prompt is reported as skipped instead of failing the batch.
- Retries served from OpenRouter's response cache at $0 when the first call already succeeded.

## Running the sample

Set `OPENROUTER_API_KEY` (see the [parent README](../README.md)), then:

```bash
# Terminal 1
uv run --group openrouter openrouter/prompt_batch/run_worker.py

# Terminal 2
uv run --group openrouter openrouter/prompt_batch/run_workflow.py "Explain retries in one sentence." "Write a haiku about databases."
```

Output:

```
Starting openrouter-prompt-batch-6923ab3d-...

[deepseek/deepseek-v4-flash-0731] $0.000022 cache=MISS
  Q: Explain retries in one sentence.
  A: Retries are the automatic re-attempts of a failed operation, often after a delay ...

[deepseek/deepseek-v4-flash-0731] $0.000525 cache=MISS
  Q: Write a haiku about databases.
  A: Columns and table, ...

Total cost: $0.000547
Inspect: temporal workflow show -w openrouter-prompt-batch-6923ab3d-...
```

### See a retry that costs nothing

`--fail-once` makes each Activity fail its first attempt *after* OpenRouter has answered, which is what a Worker crash at the wrong moment looks like. The retry re-sends the identical request and OpenRouter serves it from cache:

```bash
uv run --group openrouter openrouter/prompt_batch/run_workflow.py --fail-once "Explain idempotency in one sentence."
```

```
[deepseek/deepseek-v4-flash-0731] $0.000000 cache=HIT
  Q: Explain idempotency in one sentence.
  A: Idempotency means that an operation can be applied multiple times, but the result is the same ...

Total cost: $0.000000
```

`temporal workflow show -w <workflow-id>` shows both attempts. The cache is keyed on your API key and the exact request body, so running the same prompt again within the cache TTL (10 minutes by default here) is also a hit. OpenRouter writes the cache shortly after the response completes; a retry that arrives before that write lands is a `MISS` and is billed, which you may see occasionally with the one-second retry interval used here.

### Other options

- `--model <slug>`: any OpenRouter model instead of the Auto Router.
- `--max-concurrency N`: how many prompts are in flight at once (default 5).

## Files

| File | Description |
|------|-------------|
| [workflow.py](workflow.py) | `PromptBatchWorkflow`: fan-out under a semaphore, per-prompt failure handling, retry policy. |
| [run_worker.py](run_worker.py) | Builds the OpenRouter client once and runs the Worker. |
| [run_workflow.py](run_workflow.py) | Starts a batch and prints answer, model, cost, and cache status per prompt. |
| [../activities.py](../activities.py) | `call_openrouter`: one HTTP call per attempt, error classification, cache headers, heartbeats. |
| [../shared.py](../shared.py) | Dataclasses shared by starter, Workflow, and Activity. |
