import asyncio
from datetime import timedelta
from typing import Union

from temporalio import workflow
from temporalio.exceptions import ActivityError, ApplicationError, CancelledError

# The shared dataclasses are passed through the sandbox so that objects the
# Activity returns are the same classes the Workflow compares against.
with workflow.unsafe.imports_passed_through():
    from openrouter.activities import OpenRouterActivities
    from openrouter.shared import (
        MAX_PROMPTS_PER_BATCH,
        OPENROUTER_RETRY_POLICY,
        BatchInput,
        BatchResult,
        OpenRouterRequest,
        OpenRouterResult,
        SkippedPrompt,
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

        if batch.max_concurrency < 1:
            raise ApplicationError(
                "max_concurrency must be at least 1", non_retryable=True
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
            reported_cost_usd=round(sum(r.cost_usd or 0.0 for r in results), 6),
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
                cause = e.cause
                if isinstance(cause, CancelledError):
                    # The Activity was cancelled (the Workflow is being cancelled);
                    # that is not a per-prompt failure.
                    raise
                # One bad prompt should not fail the batch. Record why and
                # carry on; the caller decides what to do with skipped prompts.
                reason = (
                    cause.type
                    if isinstance(cause, ApplicationError) and cause.type
                    else type(cause).__name__
                )
                workflow.logger.warning("Skipping prompt %r: %s", prompt, reason)
                return SkippedPrompt(prompt=prompt, reason=reason)
