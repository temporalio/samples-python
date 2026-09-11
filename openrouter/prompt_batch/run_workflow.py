import argparse
import asyncio
import uuid

from temporalio.client import Client
from temporalio.envconfig import ClientConfig

from openrouter.prompt_batch.workflow import PromptBatchWorkflow
from openrouter.shared import DEFAULT_MODEL, PROMPT_BATCH_TASK_QUEUE, BatchInput

DEFAULT_PROMPTS = [
    "Explain retries in one sentence.",
    "Write a haiku about databases.",
]


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run a prompt batch through OpenRouter."
    )
    parser.add_argument("prompts", nargs="*", default=DEFAULT_PROMPTS)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--max-concurrency", type=int, default=5)
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

    workflow_id = f"openrouter-prompt-batch-{uuid.uuid4()}"
    print(f"Starting {workflow_id}", flush=True)
    result = await client.execute_workflow(
        PromptBatchWorkflow.run,
        BatchInput(
            prompts=args.prompts,
            model=args.model,
            max_concurrency=args.max_concurrency,
            fail_once_after_call=args.fail_once,
        ),
        id=workflow_id,
        task_queue=PROMPT_BATCH_TASK_QUEUE,
    )

    for r in result.results:
        print(f"\n[{r.model}] ${r.cost_usd:.6f} cache={r.cache_status or '-'}")
        print(f"  Q: {r.prompt}")
        print(f"  A: {r.answer.strip()}")
    for s in result.skipped:
        print(f"\n[skipped: {s.reason}] {s.prompt}")
    print(f"\nTotal cost: ${result.total_cost_usd:.6f}")
    print(f"Inspect: temporal workflow show -w {workflow_id}")


if __name__ == "__main__":
    asyncio.run(main())
