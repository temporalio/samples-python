import asyncio
import uuid

import pytest
from temporalio import activity
from temporalio.client import (
    Client,
    WithStartWorkflowOperation,
    WorkflowFailureError,
    WorkflowHandle,
    WorkflowUpdateFailedError,
)
from temporalio.common import WorkflowIDConflictPolicy
from temporalio.exceptions import ApplicationError, CancelledError
from temporalio.worker import Worker

from openrouter.budget_gate.workflow import BudgetGateWorkflow
from openrouter.shared import (
    BatchInput,
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


@pytest.fixture
def task_queue() -> str:
    return f"test-openrouter-budget-{uuid.uuid4()}"


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
                batch=BatchInput(prompts=["a", "b", "c"], max_concurrency=1),
                budget_usd=0.0015,
                estimated_cost_usd=COST_PER_CALL,
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
    assert result.reported_cost_usd == pytest.approx(3 * COST_PER_CALL)
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
                batch=BatchInput(prompts=["a", "b", "c"], max_concurrency=1),
                budget_usd=1.0,
                estimated_cost_usd=COST_PER_CALL,
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
                batch=BatchInput(prompts=["a", "b"], max_concurrency=1),
                budget_usd=0.0015,
                estimated_cost_usd=COST_PER_CALL,
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
                batch=BatchInput(prompts=["a", "b", "c"], max_concurrency=2),
                budget_usd=0.0015,
                estimated_cost_usd=COST_PER_CALL,
                approval_timeout_seconds=1,
            ),
            id=f"test-openrouter-budget-{uuid.uuid4()}",
            task_queue=task_queue,
        )

    assert [r.prompt for r in result.results] == ["a"]
    assert sorted(s.prompt for s in result.skipped) == ["b", "c"]
    assert {s.reason for s in result.skipped} == {"soft_budget_exhausted"}
    assert result.reported_cost_usd == pytest.approx(COST_PER_CALL)
    assert fake.calls == {"a": 1}


async def test_zero_concurrency_is_rejected(client: Client, task_queue: str) -> None:
    fake = FakeOpenRouter()
    async with Worker(
        client,
        task_queue=task_queue,
        workflows=[BudgetGateWorkflow],
        activities=[fake.call_openrouter],
    ):
        with pytest.raises(WorkflowFailureError) as excinfo:
            await client.execute_workflow(
                BudgetGateWorkflow.run,
                BudgetGateInput(
                    batch=BatchInput(prompts=["a"], max_concurrency=0),
                    budget_usd=1.0,
                ),
                id=f"test-openrouter-budget-{uuid.uuid4()}",
                task_queue=task_queue,
            )
    assert isinstance(excinfo.value.cause, ApplicationError)
    assert "max_concurrency" in str(excinfo.value.cause)
    assert fake.calls == {}


async def test_non_finite_budget_is_rejected(client: Client, task_queue: str) -> None:
    fake = FakeOpenRouter()
    async with Worker(
        client,
        task_queue=task_queue,
        workflows=[BudgetGateWorkflow],
        activities=[fake.call_openrouter],
    ):
        with pytest.raises(WorkflowFailureError):
            await client.execute_workflow(
                BudgetGateWorkflow.run,
                BudgetGateInput(
                    batch=BatchInput(prompts=["a"]), budget_usd=float("inf")
                ),
                id=f"test-openrouter-budget-{uuid.uuid4()}",
                task_queue=task_queue,
            )
    assert fake.calls == {}


async def test_raising_the_budget_admits_only_what_fits(
    client: Client, task_queue: str
) -> None:
    """Three prompts park; a raise that fits one call must wake only one."""
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
                batch=BatchInput(prompts=["a", "b", "c", "d"], max_concurrency=3),
                budget_usd=0.0015,
                estimated_cost_usd=COST_PER_CALL,
                approval_timeout_seconds=60,
            ),
        )
        # "a" runs; "b" and "c" park on the soft budget, and "d" parks too
        # once "a" frees its concurrency slot.
        for _ in range(100):
            report = await handle.query(BudgetGateWorkflow.spend_report)
            if report.completed == 1 and len(report.paused) == 3:
                break
            await asyncio.sleep(0.1)
        assert report.completed == 1 and len(report.paused) == 3

        # Headroom for exactly one more call: spent 0.001 + 0.001 <= 0.0025.
        await handle.execute_update(BudgetGateWorkflow.raise_budget, 0.0025)
        for _ in range(100):
            report = await handle.query(BudgetGateWorkflow.spend_report)
            if report.completed == 2:
                break
            await asyncio.sleep(0.1)
        # Give the others a chance to (wrongly) run; they must stay parked.
        await asyncio.sleep(0.5)
        report = await handle.query(BudgetGateWorkflow.spend_report)
        assert report.completed == 2
        assert report.spent_usd == pytest.approx(2 * COST_PER_CALL)
        assert len(report.paused) == 2
        assert report.reserved_usd == 0

        await handle.execute_update(BudgetGateWorkflow.raise_budget, 1.0)
        result = await handle.result()

    assert [r.prompt for r in result.results] == ["a", "b", "c", "d"]
    assert fake.calls == {"a": 1, "b": 1, "c": 1, "d": 1}


async def test_update_with_start_sets_the_budget_before_run(
    client: Client, task_queue: str
) -> None:
    """An Update that lands before run() must not be overwritten by run()."""
    fake = FakeOpenRouter()
    async with Worker(
        client,
        task_queue=task_queue,
        workflows=[BudgetGateWorkflow],
        activities=[fake.call_openrouter],
    ):
        start_op = WithStartWorkflowOperation(
            BudgetGateWorkflow.run,
            BudgetGateInput(
                batch=BatchInput(prompts=["a", "b", "c"], max_concurrency=1),
                budget_usd=0.0015,
                estimated_cost_usd=COST_PER_CALL,
                approval_timeout_seconds=5,
            ),
            id=f"test-openrouter-budget-{uuid.uuid4()}",
            task_queue=task_queue,
            id_conflict_policy=WorkflowIDConflictPolicy.FAIL,
        )
        report = await client.execute_update_with_start_workflow(
            BudgetGateWorkflow.raise_budget, 1.0, start_workflow_operation=start_op
        )
        assert report.budget_usd == 1.0
        handle = await start_op.workflow_handle()
        result = await handle.result()

    # With the raised budget honored, nothing parks and nothing is skipped.
    assert [r.prompt for r in result.results] == ["a", "b", "c"]
    assert result.skipped == []


async def test_cancellation_is_not_a_skipped_prompt(
    client: Client, task_queue: str, caplog: pytest.LogCaptureFixture
) -> None:
    @activity.defn(name="call_openrouter")
    async def slow_call(request: OpenRouterRequest) -> OpenRouterResult:
        # Heartbeat so the cancellation request reaches the Activity.
        while True:
            activity.heartbeat()
            await asyncio.sleep(0.1)

    async with Worker(
        client,
        task_queue=task_queue,
        workflows=[BudgetGateWorkflow],
        activities=[slow_call],
    ):
        handle = await start(
            client,
            task_queue,
            BudgetGateInput(
                batch=BatchInput(prompts=["a", "b"], max_concurrency=2),
                budget_usd=1.0,
                estimated_cost_usd=COST_PER_CALL,
                approval_timeout_seconds=60,
            ),
        )
        await asyncio.sleep(0.5)
        await handle.cancel()
        with pytest.raises(WorkflowFailureError) as excinfo:
            await handle.result()

    assert isinstance(excinfo.value.cause, CancelledError)
    # The cancelled Activities must not have been recorded as skipped prompts.
    assert not [r for r in caplog.records if "Skipping prompt" in r.getMessage()]


async def test_bad_approval_timeout_fails_the_workflow(
    client: Client, task_queue: str
) -> None:
    fake = FakeOpenRouter()
    async with Worker(
        client,
        task_queue=task_queue,
        workflows=[BudgetGateWorkflow],
        activities=[fake.call_openrouter],
    ):
        for bad in (-5, 10**15):
            with pytest.raises(WorkflowFailureError) as excinfo:
                await client.execute_workflow(
                    BudgetGateWorkflow.run,
                    BudgetGateInput(
                        batch=BatchInput(prompts=["a"]),
                        budget_usd=1.0,
                        approval_timeout_seconds=bad,
                    ),
                    id=f"test-openrouter-budget-{uuid.uuid4()}",
                    task_queue=task_queue,
                )
            assert isinstance(excinfo.value.cause, ApplicationError)
            assert "approval_timeout_seconds" in str(excinfo.value.cause)
    assert fake.calls == {}


async def test_unknown_cost_is_charged_at_the_estimate(
    client: Client, task_queue: str
) -> None:
    @activity.defn(name="call_openrouter")
    async def costless(request: OpenRouterRequest) -> OpenRouterResult:
        return OpenRouterResult(
            prompt=request.prompt,
            model="m",
            answer="ok",
            cost_usd=None,
            generation_id="gen",
            cache_status="",
        )

    async with Worker(
        client,
        task_queue=task_queue,
        workflows=[BudgetGateWorkflow],
        activities=[costless],
    ):
        result = await client.execute_workflow(
            BudgetGateWorkflow.run,
            BudgetGateInput(
                batch=BatchInput(prompts=["a", "b"], max_concurrency=1),
                budget_usd=1.0,
                estimated_cost_usd=0.002,
            ),
            id=f"test-openrouter-budget-{uuid.uuid4()}",
            task_queue=task_queue,
        )

    assert result.reported_cost_usd == pytest.approx(0.004)
    assert result.unknown_cost_count == 2
    assert [r.cost_usd for r in result.results] == [None, None]


async def test_credits_never_arrive_skips_with_reason(
    client: Client, task_queue: str
) -> None:
    fake = FakeOpenRouter(out_of_credits_for={"a"})
    async with Worker(
        client,
        task_queue=task_queue,
        workflows=[BudgetGateWorkflow],
        activities=[fake.call_openrouter],
    ):
        result = await client.execute_workflow(
            BudgetGateWorkflow.run,
            BudgetGateInput(
                batch=BatchInput(prompts=["a"], max_concurrency=1),
                budget_usd=1.0,
                estimated_cost_usd=COST_PER_CALL,
                approval_timeout_seconds=1,
            ),
            id=f"test-openrouter-budget-{uuid.uuid4()}",
            task_queue=task_queue,
        )

    assert result.results == []
    assert [(s.prompt, s.reason) for s in result.skipped] == [
        ("a", "insufficient_credits")
    ]


async def test_exact_budget_boundary_is_affordable(
    client: Client, task_queue: str
) -> None:
    """Ten $0.001 calls must fit a $0.01 budget despite float accumulation."""
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
                batch=BatchInput(
                    prompts=[str(i) for i in range(10)], max_concurrency=1
                ),
                budget_usd=0.01,
                estimated_cost_usd=COST_PER_CALL,
                approval_timeout_seconds=0,
            ),
            id=f"test-openrouter-budget-{uuid.uuid4()}",
            task_queue=task_queue,
        )

    assert len(result.results) == 10
    assert result.skipped == []


async def test_top_up_during_an_in_flight_call_counts(
    client: Client, task_queue: str
) -> None:
    """A raise_budget that lands while a call is in flight must release that
    prompt when the call then fails for lack of credits."""
    release_b = asyncio.Event()
    calls: dict[str, int] = {}

    @activity.defn(name="call_openrouter")
    async def flaky_credits(request: OpenRouterRequest) -> OpenRouterResult:
        calls[request.prompt] = calls.get(request.prompt, 0) + 1
        if calls[request.prompt] == 1:
            if request.prompt == "b":
                # Hold b's failure until the test has sent the top-up.
                await release_b.wait()
            raise ApplicationError(
                "OpenRouter returned HTTP 402: Insufficient credits",
                type="OpenRouterOutOfCredits",
                non_retryable=True,
            )
        return OpenRouterResult(
            prompt=request.prompt,
            model="m",
            answer="ok",
            cost_usd=COST_PER_CALL,
            generation_id=f"gen-{request.prompt}",
            cache_status="",
        )

    async with Worker(
        client,
        task_queue=task_queue,
        workflows=[BudgetGateWorkflow],
        activities=[flaky_credits],
    ):
        handle = await start(
            client,
            task_queue,
            BudgetGateInput(
                batch=BatchInput(prompts=["a", "b"], max_concurrency=2),
                budget_usd=1.0,
                estimated_cost_usd=COST_PER_CALL,
                approval_timeout_seconds=5,
            ),
        )
        report = await wait_until_paused(handle, "insufficient_credits")
        assert report.paused == {"a": "insufficient_credits"}
        # The operator tops up while b's call is still in flight...
        await handle.execute_update(BudgetGateWorkflow.raise_budget, 1.0)
        # ...and only then does b's failure reach the Workflow.
        release_b.set()
        result = await handle.result()

    assert [r.prompt for r in result.results] == ["a", "b"]
    assert result.skipped == []
    assert calls == {"a": 2, "b": 2}


async def test_top_up_during_a_call_counts_even_after_the_deadline(
    client: Client, task_queue: str
) -> None:
    release = asyncio.Event()
    calls: dict[str, int] = {}

    @activity.defn(name="call_openrouter")
    async def flaky_credits(request: OpenRouterRequest) -> OpenRouterResult:
        calls[request.prompt] = calls.get(request.prompt, 0) + 1
        if calls[request.prompt] == 1:
            await release.wait()
            raise ApplicationError(
                "OpenRouter returned HTTP 402: Insufficient credits",
                type="OpenRouterOutOfCredits",
                non_retryable=True,
            )
        return OpenRouterResult(
            prompt=request.prompt,
            model="m",
            answer="ok",
            cost_usd=COST_PER_CALL,
            generation_id="gen",
            cache_status="",
        )

    async with Worker(
        client,
        task_queue=task_queue,
        workflows=[BudgetGateWorkflow],
        activities=[flaky_credits],
    ):
        handle = await start(
            client,
            task_queue,
            BudgetGateInput(
                batch=BatchInput(prompts=["a"]),
                budget_usd=1.0,
                estimated_cost_usd=COST_PER_CALL,
                approval_timeout_seconds=0,
            ),
        )
        for _ in range(100):
            if calls.get("a") == 1:
                break
            await asyncio.sleep(0.05)
        await handle.execute_update(BudgetGateWorkflow.raise_budget, 1.0)
        release.set()
        result = await handle.result()

    assert [r.prompt for r in result.results] == ["a"]
    assert calls == {"a": 2}
