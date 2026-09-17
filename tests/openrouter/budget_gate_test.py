import asyncio
import uuid
from typing import AsyncIterator

import pytest
import pytest_asyncio
from temporalio import activity
from temporalio.client import Client, WorkflowHandle, WorkflowUpdateFailedError
from temporalio.exceptions import ApplicationError
from temporalio.worker import Worker

from openrouter.budget_gate.workflow import BudgetGateWorkflow
from openrouter.shared import (
    BatchResult,
    BudgetGateInput,
    OpenRouterRequest,
    OpenRouterResult,
    SpendReport,
)

COST_PER_CALL = 0.001


class FakeOpenRouter:
    """Mock Activity with a per-prompt count; optionally out of credits on first call."""

    def __init__(self, out_of_credits_for: set[str] | None = None) -> None:
        self.calls: dict[str, int] = {}
        self.out_of_credits_for = out_of_credits_for or set()

    @activity.defn(name="call_openrouter")
    async def call_openrouter(self, request: OpenRouterRequest) -> OpenRouterResult:
        self.calls[request.prompt] = self.calls.get(request.prompt, 0) + 1
        if (
            request.prompt in self.out_of_credits_for
            and self.calls[request.prompt] == 1
        ):
            raise ApplicationError(
                "OpenRouter returned HTTP 403: Key limit exceeded (total limit)",
                type="OpenRouterOutOfCredits",
                non_retryable=True,
            )
        return OpenRouterResult(
            prompt=request.prompt,
            model="openai/gpt-4o-mini",
            answer="ok",
            cost_usd=COST_PER_CALL,
            generation_id=f"gen-{request.prompt}-{self.calls[request.prompt]}",
            cache_status="MISS",
        )


@pytest_asyncio.fixture
async def task_queue(client: Client) -> AsyncIterator[str]:
    yield f"test-openrouter-budget-{uuid.uuid4()}"


async def start(
    client: Client, task_queue: str, gate: BudgetGateInput
) -> WorkflowHandle[BudgetGateWorkflow, BatchResult]:
    return await client.start_workflow(
        BudgetGateWorkflow.run,
        gate,
        id=f"test-openrouter-budget-{uuid.uuid4()}",
        task_queue=task_queue,
    )


async def wait_until_paused(
    handle: WorkflowHandle[BudgetGateWorkflow, BatchResult], reason: str
) -> SpendReport:
    for _ in range(100):
        report = await handle.query(BudgetGateWorkflow.spend_report)
        if reason in report.paused.values():
            return report
        await asyncio.sleep(0.1)
    raise AssertionError(f"workflow never paused with reason {reason!r}")


async def test_soft_budget_pauses_then_resumes_on_raise_budget(
    client: Client, task_queue: str
) -> None:
    fake = FakeOpenRouter()
    async with Worker(
        client,
        task_queue=task_queue,
        workflows=[BudgetGateWorkflow],
        activities=[fake.call_openrouter],
    ):
        # Budget covers exactly one call; the second prompt must park.
        handle = await start(
            client,
            task_queue,
            BudgetGateInput(
                prompts=["a", "b", "c"],
                budget_usd=0.0015,
                estimated_cost_usd=COST_PER_CALL,
                max_concurrency=1,
                approval_timeout_seconds=60,
            ),
        )
        report = await wait_until_paused(handle, "soft_budget_exhausted")
        assert report.completed == 1
        assert report.spent_usd == pytest.approx(COST_PER_CALL)
        assert report.paused == {"b": "soft_budget_exhausted"}

        report = await handle.execute_update(BudgetGateWorkflow.raise_budget, 0.01)
        assert report.budget_usd == 0.01

        result = await handle.result()

    assert [r.prompt for r in result.results] == ["a", "b", "c"]
    assert result.skipped == []
    assert result.total_cost_usd == pytest.approx(3 * COST_PER_CALL)
    assert fake.calls == {"a": 1, "b": 1, "c": 1}


async def test_insufficient_credits_pauses_and_reruns_same_prompt(
    client: Client, task_queue: str
) -> None:
    fake = FakeOpenRouter(out_of_credits_for={"b"})
    async with Worker(
        client,
        task_queue=task_queue,
        workflows=[BudgetGateWorkflow],
        activities=[fake.call_openrouter],
    ):
        handle = await start(
            client,
            task_queue,
            BudgetGateInput(
                prompts=["a", "b", "c"],
                budget_usd=1.0,
                estimated_cost_usd=COST_PER_CALL,
                max_concurrency=1,
                approval_timeout_seconds=60,
            ),
        )
        report = await wait_until_paused(handle, "insufficient_credits")
        assert report.paused == {"b": "insufficient_credits"}
        assert report.completed == 1

        # Re-sending the same budget is how an operator says "I topped up".
        await handle.execute_update(BudgetGateWorkflow.raise_budget, 1.0)
        result = await handle.result()

    assert [r.prompt for r in result.results] == ["a", "b", "c"]
    assert result.skipped == []
    # "b" was called twice: once for the 402, once after the budget bump.
    assert fake.calls == {"a": 1, "b": 2, "c": 1}
    assert result.results[1].generation_id == "gen-b-2"


async def test_lowering_the_budget_is_rejected(client: Client, task_queue: str) -> None:
    fake = FakeOpenRouter()
    async with Worker(
        client,
        task_queue=task_queue,
        workflows=[BudgetGateWorkflow],
        activities=[fake.call_openrouter],
    ):
        handle = await start(
            client,
            task_queue,
            BudgetGateInput(
                prompts=["a", "b"],
                budget_usd=0.0015,
                estimated_cost_usd=COST_PER_CALL,
                max_concurrency=1,
                approval_timeout_seconds=60,
            ),
        )
        await wait_until_paused(handle, "soft_budget_exhausted")

        with pytest.raises(WorkflowUpdateFailedError):
            await handle.execute_update(BudgetGateWorkflow.raise_budget, 0.0001)

        await handle.execute_update(BudgetGateWorkflow.raise_budget, 0.01)
        result = await handle.result()

    assert [r.prompt for r in result.results] == ["a", "b"]


async def test_approval_timeout_skips_remaining_prompts(
    client: Client, task_queue: str
) -> None:
    fake = FakeOpenRouter()
    async with Worker(
        client,
        task_queue=task_queue,
        workflows=[BudgetGateWorkflow],
        activities=[fake.call_openrouter],
    ):
        result = await client.execute_workflow(
            BudgetGateWorkflow.run,
            BudgetGateInput(
                prompts=["a", "b", "c"],
                budget_usd=0.0015,
                estimated_cost_usd=COST_PER_CALL,
                max_concurrency=2,
                approval_timeout_seconds=1,
            ),
            id=f"test-openrouter-budget-{uuid.uuid4()}",
            task_queue=task_queue,
        )

    assert [r.prompt for r in result.results] == ["a"]
    assert sorted(s.prompt for s in result.skipped) == ["b", "c"]
    assert {s.reason for s in result.skipped} == {"soft_budget_exhausted"}
    assert result.total_cost_usd == pytest.approx(COST_PER_CALL)
    assert fake.calls == {"a": 1}
