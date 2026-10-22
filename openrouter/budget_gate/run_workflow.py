import argparse
import asyncio
import uuid

from temporalio.client import Client
from temporalio.envconfig import ClientConfig

from openrouter.budget_gate.workflow import BudgetGateWorkflow
from openrouter.shared import (
    BUDGET_GATE_TASK_QUEUE,
    DEFAULT_MODEL,
    BatchInput,
    BudgetGateInput,
)

DEFAULT_PROMPTS = [
    "Explain retries in one sentence.",
    "Write a haiku about databases.",
    "Name three uses for embeddings.",
    "Summarize eventual consistency in two sentences.",
    "What is a task queue?",
    "Give one reason to use idempotency keys.",
]


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run a prompt batch that pauses when the budget runs out."
    )
    parser.add_argument("prompts", nargs="*", default=DEFAULT_PROMPTS)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument(
        "--budget-usd",
        type=float,
        default=0.001,
        help="Soft budget. The default is small enough to pause a few prompts in.",
    )
    parser.add_argument("--estimate-usd", type=float, default=0.0005)
    parser.add_argument("--max-concurrency", type=int, default=2)
    parser.add_argument("--approval-timeout-seconds", type=int, default=3600)
    parser.add_argument(
        "--fail-once",
        action="store_true",
        help="Fail each Activity's first attempt after the response arrives, "
        "so the retry shows a cache hit billed at $0.",
    )
    args = parser.parse_args()

    config = ClientConfig.load_client_connect_config()
    config.setdefault("target_host", "localhost:7233")
    client = await Client.connect(**config)

    workflow_id = f"openrouter-budget-gate-{uuid.uuid4()}"
    handle = await client.start_workflow(
        BudgetGateWorkflow.run,
        BudgetGateInput(
            batch=BatchInput(
                prompts=args.prompts,
                model=args.model,
                max_concurrency=args.max_concurrency,
                fail_once_after_call=args.fail_once,
            ),
            budget_usd=args.budget_usd,
            estimated_cost_usd=args.estimate_usd,
            approval_timeout_seconds=args.approval_timeout_seconds,
        ),
        id=workflow_id,
        task_queue=BUDGET_GATE_TASK_QUEUE,
    )
    print(f"Started {workflow_id}")
    print("While it runs:")
    print(f"  temporal workflow query -w {workflow_id} --type spend_report")
    print(
        f"  uv run --group openrouter openrouter/budget_gate/raise_budget.py {workflow_id} 0.05"
    )
    print("Waiting for the batch to finish...\n", flush=True)

    result = await handle.result()
    for r in result.results:
        cost = "unknown" if r.cost_usd is None else f"${r.cost_usd:.6f}"
        print(f"[{r.model}] {cost} cache={r.cache_status or '-'}  {r.prompt}")
    for s in result.skipped:
        print(f"[skipped: {s.reason}] {s.prompt}")
    print(
        f"\nReported cost: ${result.reported_cost_usd:.6f} "
        "(what OpenRouter reported on each prompt's final attempt)"
    )
    if result.unknown_cost_count:
        print(f"  {result.unknown_cost_count} prompt(s) came back without a cost")
    print(f"Inspect: temporal workflow show -w {workflow_id}")


if __name__ == "__main__":
    asyncio.run(main())
