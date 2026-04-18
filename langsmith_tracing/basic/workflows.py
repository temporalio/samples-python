"""Basic one-shot LLM workflow with LangSmith tracing."""

from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from langsmith import traceable

    from langsmith_tracing.basic.activities import OpenAIRequest, call_openai

RETRY = RetryPolicy(initial_interval=timedelta(seconds=2), maximum_attempts=3)


@workflow.defn
class BasicLLMWorkflow:
    @workflow.run
    async def run(self, prompt: str) -> str:
        # @traceable creates a named span in LangSmith. Inside a workflow,
        # it nests under the workflow's trace (when add_temporal_runs=True)
        # or stands alone as a root span (when add_temporal_runs=False).
        @traceable(
            name=f"Ask: {prompt[:60]}",
            run_type="chain",
            metadata={"workflow_id": workflow.info().workflow_id},
            tags=["basic-llm"],
        )
        async def _run() -> str:
            response = await workflow.execute_activity(
                call_openai,
                OpenAIRequest(model="gpt-4o-mini", input=prompt),
                start_to_close_timeout=timedelta(seconds=60),
                retry_policy=RETRY,
            )
            return response.output_text

        return await _run()
