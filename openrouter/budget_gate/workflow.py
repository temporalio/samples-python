import asyncio
import math
from datetime import timedelta
from typing import Callable, Union

from temporalio import workflow
from temporalio.exceptions import ActivityError, ApplicationError, CancelledError

# The shared dataclasses are passed through the sandbox so that objects the
# Activity returns are the same classes the Workflow compares against.
with workflow.unsafe.imports_passed_through():
    from openrouter.activities import OUT_OF_CREDITS, OpenRouterActivities
    from openrouter.shared import (
        BUDGET_TOLERANCE_USD,
        MAX_APPROVAL_TIMEOUT_SECONDS,
        MAX_PROMPTS_PER_BATCH,
        OPENROUTER_RETRY_POLICY,
        BatchResult,
        BudgetGateInput,
        LedgerEntry,
        OpenRouterRequest,
        OpenRouterResult,
        SkippedPrompt,
        SpendReport,
    )

INSUFFICIENT_CREDITS = OUT_OF_CREDITS


@workflow.defn
class BudgetGateWorkflow:
    """A prompt batch that pauses instead of failing when money runs out.

    Two things can pause it: the soft budget in the input (checked against the
    cost OpenRouter reports per response) and OpenRouter itself refusing the
    call for lack of credits (402 for the account, 403 "Key limit exceeded"
    for the API key). Either way the batch parks until
    a `raise_budget` Update arrives, then resumes exactly where it stopped.
    Completed prompts are never re-run.
    """

    @workflow.init
    def __init__(self, gate: BudgetGateInput) -> None:
        # Set the budget and deadline here rather than in run(): an Update sent
        # with update-with-start is handled before run() starts, and must see
        # (and be allowed to raise) the real budget.
        self._budget_usd = gate.budget_usd
        # Validate here, not in run(): a bad value must fail the Workflow, not
        # raise while computing the deadline below.
        if not 0 <= gate.approval_timeout_seconds <= MAX_APPROVAL_TIMEOUT_SECONDS:
            raise ApplicationError(
                "approval_timeout_seconds must be between 0 and "
                f"{MAX_APPROVAL_TIMEOUT_SECONDS}",
                non_retryable=True,
            )
        # One deadline for the whole batch: every parked prompt waits until this
        # moment, not for its own full approval timeout.
        self._deadline = workflow.now() + timedelta(
            seconds=gate.approval_timeout_seconds
        )
        self._spent_usd = 0.0
        self._reserved_usd = 0.0
        # Bumped by every raise_budget Update, so a prompt parked on a
        # credits error can tell that the operator acted even if the soft
        # budget did not change.
        self._budget_version = 0
        self._ledger: list[LedgerEntry] = []
        self._paused: dict[str, str] = {}

    @workflow.run
    async def run(self, gate: BudgetGateInput) -> BatchResult:
        batch = gate.batch
        if len(batch.prompts) > MAX_PROMPTS_PER_BATCH:
            raise ApplicationError(
                f"Batch has {len(batch.prompts)} prompts; the limit is "
                f"{MAX_PROMPTS_PER_BATCH}.",
                non_retryable=True,
            )
        if batch.max_concurrency < 1:
            raise ApplicationError(
                "max_concurrency must be at least 1", non_retryable=True
            )
        if (
            not math.isfinite(gate.estimated_cost_usd)
            or gate.estimated_cost_usd <= 0
            or not math.isfinite(gate.budget_usd)
            or gate.budget_usd < 0
        ):
            raise ApplicationError(
                "estimated_cost_usd must be a positive finite number and "
                "budget_usd a non-negative finite number",
                non_retryable=True,
            )
        semaphore = asyncio.Semaphore(batch.max_concurrency)
        try:
            outcomes = await asyncio.gather(
                *(self._answer(prompt, gate, semaphore) for prompt in batch.prompts)
            )
        finally:
            # Good hygiene for any Workflow with handlers: do not return while
            # a handler is still running. (raise_budget is synchronous, so this
            # is always already true here.)
            await workflow.wait_condition(workflow.all_handlers_finished)

        results = [o for o in outcomes if isinstance(o, OpenRouterResult)]
        skipped = [o for o in outcomes if isinstance(o, SkippedPrompt)]
        return BatchResult(
            results=results,
            skipped=skipped,
            reported_cost_usd=round(self._spent_usd, 6),
            unknown_cost_count=sum(1 for e in self._ledger if not e.cost_known),
        )

    # @@@SNIPSTART python-openrouter-budget-gate-handlers
    @workflow.update
    def raise_budget(self, new_budget_usd: float) -> SpendReport:
        """Raise the soft budget and wake every parked prompt.

        Send the current budget unchanged to resume after topping up credits
        in the OpenRouter dashboard.
        """
        self._budget_usd = new_budget_usd
        self._budget_version += 1
        return self.spend_report()

    @raise_budget.validator
    def validate_raise_budget(self, new_budget_usd: float) -> None:
        if not math.isfinite(new_budget_usd):
            raise ValueError("The budget must be a finite number.")
        if new_budget_usd < self._budget_usd:
            raise ValueError(
                f"New budget ${new_budget_usd} is below the current budget "
                f"${self._budget_usd}; the budget can only go up."
            )

    @workflow.query
    def spend_report(self) -> SpendReport:
        return SpendReport(
            budget_usd=self._budget_usd,
            spent_usd=round(self._spent_usd, 6),
            reserved_usd=round(self._reserved_usd, 6),
            completed=len(self._ledger),
            paused=dict(self._paused),
            ledger=list(self._ledger),
        )

    # @@@SNIPEND

    async def _answer(
        self, prompt: str, gate: BudgetGateInput, semaphore: asyncio.Semaphore
    ) -> Union[OpenRouterResult, SkippedPrompt]:
        async with semaphore:
            if not await self._reserve(prompt, gate.estimated_cost_usd):
                return SkippedPrompt(prompt=prompt, reason="soft_budget_exhausted")
            try:
                while True:
                    # Snapshot the budget version before the call, not after it
                    # fails: a raise_budget that lands while this call is in
                    # flight must count as the top-up this prompt is waiting
                    # for, not as one it missed.
                    seen_version = self._budget_version
                    try:
                        result = await workflow.execute_activity_method(
                            OpenRouterActivities.call_openrouter,
                            OpenRouterRequest(
                                prompt=prompt,
                                model=gate.batch.model,
                                fail_once_after_call=gate.batch.fail_once_after_call,
                            ),
                            start_to_close_timeout=timedelta(seconds=90),
                            heartbeat_timeout=timedelta(seconds=10),
                            retry_policy=OPENROUTER_RETRY_POLICY,
                        )
                        break
                    except ActivityError as e:
                        cause = e.cause
                        if isinstance(cause, CancelledError):
                            # The Activity was cancelled (the Workflow is being
                            # cancelled); that is not a per-prompt failure.
                            raise
                        if (
                            isinstance(cause, ApplicationError)
                            and cause.type == OUT_OF_CREDITS
                        ):
                            # Out of credits at OpenRouter. Park until the
                            # operator tops up and sends raise_budget.
                            if await self._wait_for_more_credits(prompt, seen_version):
                                continue
                            return SkippedPrompt(
                                prompt=prompt, reason="insufficient_credits"
                            )
                        reason = (
                            cause.type
                            if isinstance(cause, ApplicationError) and cause.type
                            else type(cause).__name__
                        )
                        workflow.logger.warning(
                            "Skipping prompt %r: %s", prompt, reason
                        )
                        return SkippedPrompt(prompt=prompt, reason=reason)
                # Charge what OpenRouter reported; if it reported nothing,
                # charge the estimate rather than treating the call as free.
                charged = (
                    result.cost_usd
                    if result.cost_usd is not None
                    else gate.estimated_cost_usd
                )
                cost_known = result.cost_usd is not None
                self._spent_usd += charged
                self._ledger.append(
                    LedgerEntry(
                        prompt=prompt,
                        model=result.model,
                        cost_usd=charged,
                        cost_known=cost_known,
                        generation_id=result.generation_id,
                        cache_status=result.cache_status,
                    )
                )
                return result
            finally:
                self._reserved_usd -= gate.estimated_cost_usd

    # @@@SNIPSTART python-openrouter-budget-gate-pause
    async def _reserve(self, prompt: str, estimate: float) -> bool:
        """Reserve `estimate` against the budget, parking until it fits."""

        def fits() -> bool:
            # Tolerance absorbs float accumulation; see BUDGET_TOLERANCE_USD.
            return (
                self._spent_usd + self._reserved_usd + estimate
                <= self._budget_usd + BUDGET_TOLERANCE_USD
            )

        # Loop rather than check once: when the budget is raised, every parked
        # prompt is woken before any of them runs, so each must re-check after
        # waking in case an earlier one already took the new headroom. (Each
        # re-park starts a new timer for the remaining time; fine at this scale.)
        while not fits():
            workflow.logger.info(
                "Soft budget reached (spent $%.6f of $%.6f); pausing %r",
                self._spent_usd,
                self._budget_usd,
                prompt,
            )
            if not await self._park(prompt, "soft_budget_exhausted", fits):
                return False
        self._reserved_usd += estimate
        return True

    async def _park(self, prompt: str, reason: str, until: Callable[[], bool]) -> bool:
        """Durable pause until `until()` holds or the batch deadline passes.

        Survives Worker restarts and can wait for hours. Returns False when the
        deadline passed first.
        """
        if until():
            # Nothing to wait for (a top-up already landed during the call).
            return True
        remaining = self._deadline - workflow.now()
        if remaining <= timedelta(0):
            return False
        self._paused[prompt] = reason
        try:
            await workflow.wait_condition(until, timeout=remaining)
            return True
        except asyncio.TimeoutError:
            return False
        finally:
            self._paused.pop(prompt, None)

    # @@@SNIPEND

    async def _wait_for_more_credits(self, prompt: str, seen_version: int) -> bool:
        """Park until a raise_budget newer than `seen_version` has arrived.

        If one already has, this returns at once and the prompt is re-run.
        """
        workflow.logger.info("OpenRouter says out of credits; pausing %r", prompt)
        return await self._park(
            prompt,
            "insufficient_credits",
            lambda: self._budget_version > seen_version,
        )
