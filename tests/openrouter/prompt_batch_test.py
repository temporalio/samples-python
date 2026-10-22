import asyncio
import uuid

import pytest
from temporalio import activity
from temporalio.client import Client, WorkflowFailureError
from temporalio.exceptions import ApplicationError, CancelledError
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
        if request.prompt == "costless":
            result = fake_result(request)
            result.cost_usd = None
            return result
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
            BatchInput(prompts=["one", "bad", "two", "costless"], max_concurrency=2),
            id=f"test-openrouter-{uuid.uuid4()}",
            task_queue=task_queue,
        )

    assert [r.prompt for r in result.results] == ["one", "two", "costless"]
    assert all(r.answer.startswith("Answer to:") for r in result.results)
    assert [(s.prompt, s.reason) for s in result.skipped] == [
        ("bad", "OpenRouterHTTP400")
    ]
    # Subtotal of the known costs, with the unknown one counted separately.
    assert result.reported_cost_usd == 0.002
    assert result.unknown_cost_count == 1


async def test_cancellation_is_not_a_skipped_prompt(
    client: Client, caplog: pytest.LogCaptureFixture
) -> None:
    @activity.defn(name="call_openrouter")
    async def slow_call(request: OpenRouterRequest) -> OpenRouterResult:
        while True:
            activity.heartbeat()
            await asyncio.sleep(0.1)

    task_queue = f"test-openrouter-{uuid.uuid4()}"
    async with Worker(
        client,
        task_queue=task_queue,
        workflows=[PromptBatchWorkflow],
        activities=[slow_call],
    ):
        handle = await client.start_workflow(
            PromptBatchWorkflow.run,
            BatchInput(prompts=["one", "two"], max_concurrency=2),
            id=f"test-openrouter-{uuid.uuid4()}",
            task_queue=task_queue,
        )
        await asyncio.sleep(0.5)
        await handle.cancel()
        with pytest.raises(WorkflowFailureError) as excinfo:
            await handle.result()

    assert isinstance(excinfo.value.cause, CancelledError)
    # The cancelled Activities must not have been recorded as skipped prompts.
    assert not [r for r in caplog.records if "Skipping prompt" in r.getMessage()]
