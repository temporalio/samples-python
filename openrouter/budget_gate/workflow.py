import asyncio
from datetime import timedelta
from typing import Optional, Union

from temporalio import workflow
from temporalio.exceptions import ActivityError, ApplicationError

from openrouter.prompt_batch.workflow import OPENROUTER_RETRY_POLICY

# The shared dataclasses are passed through the sandbox so that objects the
# Activity returns are the same classes the Workflow compares against.
with workflow.unsafe.imports_passed_through():
    from openrouter.activities import OpenRouterActivities, error_type
    from openrouter.shared import (
        MAX_PROMPTS_PER_BATCH,
        BatchResult,
        BudgetGateInput,
        LedgerEntry,
        OpenRouterRequest,
        OpenRouterResult,
        SkippedPrompt,
        SpendReport,
    )

INSUFFICIENT_CREDITS = error_type(402)


@workflow.defn
class BudgetGateWorkflow:
    """A prompt batch that pauses instead of failing when money runs out.

    Two things can pause it: the soft budget in the input (checked against the
    cost OpenRouter reports per response) and OpenRouter itself returning 402
    because the API key hit its credit limit. Either way the batch parks until
    a `raise_budget` Update arrives, then resumes exactly where it stopped.
    Completed prompts are never re-run.
    """

    def __init__(self) -> None:
        self._budget_usd = 0.0
        self._spent_usd = 0.0
        self._reserved_usd = 0.0
        # Bumped by every raise_budget Update, so a prompt parked on a 402 can
        # tell that the operator acted even if the soft budget did not change.
        self._budget_version = 0
        self._ledger: list[LedgerEntry] = []
        self._paused: dict[str, str] = {}

    @workflow.run
    async def run(self, gate: BudgetGateInput) -> BatchResult:
        if len(gate.prompts) > MAX_PROMPTS_PER_BATCH:
            raise ApplicationError(
                f"Batch has {len(gate.prompts)} prompts; the limit is "
                f"{MAX_PROMPTS_PER_BATCH}.",
                non_retryable=True,
            )
        self._budget_usd = gate.budget_usd
        semaphore = asyncio.Semaphore(gate.max_concurrency)
        try:
            outcomes = await asyncio.gather(
                *(self._answer(prompt, gate, semaphore) for prompt in gate.prompts)
            )
        finally:
            # Let an in-flight raise_budget Update finish before returning.
            await workflow.wait_condition(workflow.all_handlers_finished)

        results = [o for o in outcomes if isinstance(o, OpenRouterResult)]
        skipped = [o for o in outcomes if isinstance(o, SkippedPrompt)]
        return BatchResult(
            results=results,
            skipped=skipped,
            total_cost_usd=round(self._spent_usd, 6),
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
            paused_reason=next(iter(self._paused.values()), None),
            ledger=list(self._ledger),
        )

    # @@@SNIPEND

    async def _answer(
        self, prompt: str, gate: BudgetGateInput, semaphore: asyncio.Semaphore
    ) -> Union[OpenRouterResult, SkippedPrompt]:
        timeout = timedelta(seconds=gate.approval_timeout_seconds)
        async with semaphore:
            if not await self._reserve(prompt, gate.estimated_cost_usd, timeout):
                return SkippedPrompt(prompt=prompt, reason="soft_budget_exhausted")
            try:
                while True:
                    try:
                        result = await workflow.execute_activity_method(
                            OpenRouterActivities.call_openrouter,
                            OpenRouterRequest(prompt=prompt, model=gate.model),
                            start_to_close_timeout=timedelta(seconds=90),
                            heartbeat_timeout=timedelta(seconds=10),
                            retry_policy=OPENROUTER_RETRY_POLICY,
                        )
                        break
                    except ActivityError as e:
                        cause = e.cause
                        if (
                            isinstance(cause, ApplicationError)
                            and cause.type == INSUFFICIENT_CREDITS
                        ):
                            # The API key is out of credits. Park until the
                            # operator tops up and sends raise_budget.
                            if await self._wait_for_more_credits(prompt, timeout):
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
                self._spent_usd += result.cost_usd
                self._ledger.append(
                    LedgerEntry(
                        prompt=prompt,
                        model=result.model,
                        cost_usd=result.cost_usd,
                        generation_id=result.generation_id,
                        cache_status=result.cache_status,
                    )
                )
                return result
            finally:
                self._reserved_usd -= gate.estimated_cost_usd

    # @@@SNIPSTART python-openrouter-budget-gate-pause
    async def _reserve(self, prompt: str, estimate: float, timeout: timedelta) -> bool:
        """Reserve `estimate` against the budget, parking until it fits."""

        def fits() -> bool:
            return self._spent_usd + self._reserved_usd + estimate <= self._budget_usd

        if not fits():
            workflow.logger.info(
                "Soft budget reached (spent $%.6f of $%.6f); pausing %r",
                self._spent_usd,
                self._budget_usd,
                prompt,
            )
            self._paused[prompt] = "soft_budget_exhausted"
            try:
                # Durable pause: survives Worker restarts and can wait for hours.
                await workflow.wait_condition(fits, timeout=timeout)
            except asyncio.TimeoutError:
                return False
            finally:
                self._paused.pop(prompt, None)
        self._reserved_usd += estimate
        return True

    # @@@SNIPEND

    async def _wait_for_more_credits(self, prompt: str, timeout: timedelta) -> bool:
        seen = self._budget_version
        workflow.logger.info("OpenRouter key is out of credits; pausing %r", prompt)
        self._paused[prompt] = "insufficient_credits"
        try:
            await workflow.wait_condition(
                lambda: self._budget_version > seen, timeout=timeout
            )
            return True
        except asyncio.TimeoutError:
            return False
        finally:
            self._paused.pop(prompt, None)
