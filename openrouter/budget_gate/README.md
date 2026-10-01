# Budget gate

A prompt batch that pauses instead of failing when money runs out, and resumes when a human raises the budget.

## What this sample demonstrates

- A soft budget enforced by the Workflow from the cost OpenRouter reports on every response. When the next call would exceed it, the batch parks on `workflow.wait_condition` and stays parked for as long as it takes (hours, days) without a Worker doing anything.
- OpenRouter refusing a call for lack of credits handled the same way: a 402 for the account or the API key, or the 403 `Key limit exceeded` we have seen a per-key limit return in practice. The failing prompt parks instead of failing, and is re-run after the operator tops up.
- A `raise_budget` Update to resume, with a validator that rejects lowering the budget, and a `spend_report` Query showing spend, reservations, the ledger, and which prompts are parked and why.
- Completed prompts are never re-run. A restarted Worker, or a resumed batch, continues from the first unfinished prompt.

## Running the sample

Set `OPENROUTER_API_KEY` (see the [parent README](../README.md)), then:

```bash
# Terminal 1
uv run --group openrouter openrouter/budget_gate/run_worker.py

# Terminal 2: a budget small enough to pause after a prompt or two
uv run --group openrouter openrouter/budget_gate/run_workflow.py --budget-usd 0.0002 --estimate-usd 0.0001 --max-concurrency 1 \
  "Define durable execution in one sentence." "Why do LLM calls belong in Activities?" \
  "Name two causes of HTTP 429." "What does a heartbeat timeout detect?"
```

The starter prints the Workflow ID and waits. In a third terminal, watch it pause:

```bash
temporal workflow query -w <workflow-id> --type spend_report
```

```json
{
  "budget_usd": 0.0002,
  "spent_usd": 0.000629,
  "reserved_usd": 0,
  "completed": 2,
  "paused": { "Name two causes of HTTP 429.": "soft_budget_exhausted" },
  "ledger": [
    { "prompt": "Define durable execution in one sentence.", "model": "deepseek/deepseek-v4-flash-0731", "cost_usd": 0.00009605, "cost_known": true, "generation_id": "gen-...", "cache_status": "MISS" },
    { "prompt": "Why do LLM calls belong in Activities?", "model": "deepseek/deepseek-v4-flash-0731", "cost_usd": 0.0005325, "cost_known": true, "generation_id": "gen-...", "cache_status": "MISS" }
  ]
}
```

The second prompt alone cost more than the whole budget, so the gate closed at the third; see the note on the soft budget below.

Raise the budget to resume:

```bash
uv run --group openrouter openrouter/budget_gate/raise_budget.py <workflow-id> 0.01
# or: temporal workflow update execute -w <workflow-id> --name raise_budget --input '0.01'
```

The starter then prints the completed batch:

```
[deepseek/deepseek-v4-flash-0731] $0.000096 cache=MISS  Define durable execution in one sentence.
[deepseek/deepseek-v4-flash-0731] $0.000532 cache=MISS  Why do LLM calls belong in Activities?
[deepseek/deepseek-v4-flash-0731] $0.000180 cache=MISS  Name two causes of HTTP 429.
[deepseek/deepseek-v4-flash-0731] $0.000065 cache=MISS  What does a heartbeat timeout detect?

Reported cost: $0.000873 (what OpenRouter reported on each prompt's final attempt)
```

`temporal workflow show -w <workflow-id>` shows the pause as a `TimerStarted` (the approval timeout), then `WorkflowExecutionUpdateAccepted` and `WorkflowExecutionUpdateCompleted` when the budget is raised, `TimerCanceled`, and the remaining Activities.

### Out of credits at OpenRouter

Set a credit limit on your API key in the [OpenRouter dashboard](https://openrouter.ai/settings/keys) below what the batch needs, and run with a generous soft budget:

```bash
uv run --group openrouter openrouter/budget_gate/run_workflow.py --budget-usd 1.0 --max-concurrency 2 \
  "Define durable execution in one sentence." "Why do LLM calls belong in Activities?" \
  "Name two causes of HTTP 429." "What does a heartbeat timeout detect?"
```

When OpenRouter refuses the call (a 402, or the `403 Key limit exceeded` we have seen for a per-key limit), the prompt parks with reason `insufficient_credits`:

```json
{
  "budget_usd": 1,
  "spent_usd": 0,
  "reserved_usd": 0.002,
  "completed": 0,
  "paused": {
    "Define durable execution in one sentence.": "insufficient_credits",
    "Why do LLM calls belong in Activities?": "insufficient_credits"
  },
  "ledger": []
}
```

Raise the key's limit in the dashboard, then send `raise_budget` with the current budget value to resume; the parked prompts are re-run:

```bash
uv run --group openrouter openrouter/budget_gate/raise_budget.py <workflow-id> 1.0
```

If nobody raises the budget within `--approval-timeout-seconds` of the batch starting (default one hour, at most 30 days; one deadline shared by every parked prompt), the batch completes with the remaining prompts listed as skipped.

## What the soft budget does and does not guarantee

`spent_usd` is the sum of what OpenRouter reported on each prompt's final, successful attempt (or the estimate, if a response carried no cost). It is not a bill: an attempt that was billed but whose response never reached Temporal, such as a Worker crash after the response, is not in it. For actual spend, use OpenRouter's dashboard or `GET /api/v1/key`.

The cost of a call is only known after the response, so the Workflow reserves `--estimate-usd` per in-flight call and checks `spent + reserved + estimate <= budget` before starting one. Reservations count against the budget, so overshoot is bounded by `max_concurrency` times how far the real cost of a call exceeds the estimate: nothing if the estimate is high enough, a lot if it is far too low. In the run above the estimate was a fifth of what the second prompt cost, which is why that prompt alone blew the budget before the gate closed at the third. To bound the cost of a single call, set `provider.max_price` in the request (see OpenRouter's provider routing docs). The hard cap is the credit limit on the OpenRouter API key, which is what produces the out-of-credits error.

While parked, prompts keep their concurrency slots, so at most `max_concurrency` prompts show up in `paused`; the rest wait for a slot. Either way nothing spends until the budget is raised.

## Files

| File | Description |
|------|-------------|
| [workflow.py](workflow.py) | `BudgetGateWorkflow`: reservation ledger, pause on soft budget or out-of-credits, `raise_budget` Update with validator, `spend_report` Query. |
| [run_worker.py](run_worker.py) | Builds the OpenRouter client once and runs the Worker. |
| [run_workflow.py](run_workflow.py) | Starts a batch with a budget and prints the result. |
| [raise_budget.py](raise_budget.py) | Sends the `raise_budget` Update. |
| [../activities.py](../activities.py) | `call_openrouter`, shared with [prompt_batch](../prompt_batch). |
