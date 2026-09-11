import uuid

from temporalio import activity
from temporalio.client import Client
from temporalio.exceptions import ApplicationError
from temporalio.worker import Worker

from openrouter.prompt_batch.workflow import PromptBatchWorkflow
from openrouter.shared import BatchInput, OpenRouterRequest, OpenRouterResult


def fake_result(request: OpenRouterRequest, cost: float = 0.001) -> OpenRouterResult:
    return OpenRouterResult(
        prompt=request.prompt,
        model="openai/gpt-4o-mini",
        answer=f"Answer to: {request.prompt}",
        cost_usd=cost,
        generation_id=f"gen-{request.prompt}",
        cache_status="MISS",
    )


async def test_prompt_batch_collects_results_and_skips_failures(
    client: Client,
) -> None:
    @activity.defn(name="call_openrouter")
    async def mock_call_openrouter(request: OpenRouterRequest) -> OpenRouterResult:
        if request.prompt == "bad":
            raise ApplicationError(
                "OpenRouter returned HTTP 400: bad request",
                type="OpenRouterHTTP400",
                non_retryable=True,
            )
        return fake_result(request)

    task_queue = f"test-openrouter-{uuid.uuid4()}"
    async with Worker(
        client,
        task_queue=task_queue,
        workflows=[PromptBatchWorkflow],
        activities=[mock_call_openrouter],
    ):
        result = await client.execute_workflow(
            PromptBatchWorkflow.run,
            BatchInput(prompts=["one", "bad", "two"], max_concurrency=2),
            id=f"test-openrouter-{uuid.uuid4()}",
            task_queue=task_queue,
        )

    assert [r.prompt for r in result.results] == ["one", "two"]
    assert all(r.answer.startswith("Answer to:") for r in result.results)
    assert [(s.prompt, s.reason) for s in result.skipped] == [
        ("bad", "OpenRouterHTTP400")
    ]
    assert result.total_cost_usd == 0.002
