"""Basic one-shot LLM workflow."""

from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from langsmith_tracing.basic.activities import OpenAIRequest, call_openai

RETRY = RetryPolicy(initial_interval=timedelta(seconds=2), maximum_attempts=3)


@workflow.defn
class BasicLLMWorkflow:
    @workflow.run
    async def run(self, prompt: str) -> str:
        response = await workflow.execute_activity(
            call_openai,
            OpenAIRequest(model="gpt-4o-mini", input=prompt),
            start_to_close_timeout=timedelta(seconds=60),
            retry_policy=RETRY,
        )
        return response.output_text
