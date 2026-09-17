import asyncio
from datetime import timedelta
from typing import Union

from temporalio import workflow
from temporalio.common import RetryPolicy
from temporalio.exceptions import ActivityError, ApplicationError

# The shared dataclasses are passed through the sandbox so that objects the
# Activity returns are the same classes the Workflow compares against.
with workflow.unsafe.imports_passed_through():
    from openrouter.activities import OpenRouterActivities
    from openrouter.shared import (
        MAX_PROMPTS_PER_BATCH,
        BatchInput,
        BatchResult,
        OpenRouterRequest,
        OpenRouterResult,
        SkippedPrompt,
    )

# Temporal owns retries: 1s, 2s, 4s, ... capped at 60s, five attempts. The
# Activity marks 4xx errors non-retryable and passes OpenRouter's Retry-After
# through as the next retry delay, so this policy only governs the rest.
OPENROUTER_RETRY_POLICY = RetryPolicy(
    initial_interval=timedelta(seconds=1),
    backoff_coefficient=2.0,
    maximum_interval=timedelta(seconds=60),
    maximum_attempts=5,
)


@workflow.defn
class PromptBatchWorkflow:
    """Fan one OpenRouter call out per prompt and collect the answers."""

    @workflow.run
    async def run(self, batch: BatchInput) -> BatchResult:
        if len(batch.prompts) > MAX_PROMPTS_PER_BATCH:
            raise ApplicationError(
                f"Batch has {len(batch.prompts)} prompts; the limit is "
                f"{MAX_PROMPTS_PER_BATCH}. Split it, or see the README for the "
                "sliding-window pattern.",
                non_retryable=True,
            )

        # @@@SNIPSTART python-openrouter-prompt-batch-fan-out
        semaphore = asyncio.Semaphore(batch.max_concurrency)
        outcomes = await asyncio.gather(
            *(self._answer(prompt, batch, semaphore) for prompt in batch.prompts)
        )
        # @@@SNIPEND

        results = [o for o in outcomes if isinstance(o, OpenRouterResult)]
        skipped = [o for o in outcomes if isinstance(o, SkippedPrompt)]
        return BatchResult(
            results=results,
            skipped=skipped,
            total_cost_usd=round(sum(r.cost_usd for r in results), 6),
        )

    async def _answer(
        self, prompt: str, batch: BatchInput, semaphore: asyncio.Semaphore
    ) -> Union[OpenRouterResult, SkippedPrompt]:
        async with semaphore:
            try:
                return await workflow.execute_activity_method(
                    OpenRouterActivities.call_openrouter,
                    OpenRouterRequest(
                        prompt=prompt,
                        model=batch.model,
                        fail_once_after_call=batch.fail_once_after_call,
                    ),
                    start_to_close_timeout=timedelta(seconds=90),
                    heartbeat_timeout=timedelta(seconds=10),
                    retry_policy=OPENROUTER_RETRY_POLICY,
                )
            except ActivityError as e:
                # One bad prompt should not fail the batch. Record why and
                # carry on; the caller decides what to do with skipped prompts.
                cause = e.cause
                reason = (
                    cause.type
                    if isinstance(cause, ApplicationError) and cause.type
                    else type(cause).__name__
                )
                workflow.logger.warning("Skipping prompt %r: %s", prompt, reason)
                return SkippedPrompt(prompt=prompt, reason=reason)
