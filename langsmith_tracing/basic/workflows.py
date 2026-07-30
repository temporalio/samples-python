"""Basic one-shot LLM workflow with LangSmith tracing."""

from datetime import timedelta

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from langsmith import traceable

    from langsmith_tracing.basic.activities import OpenAIRequest, call_openai


@workflow.defn
class BasicLLMWorkflow:
    # Do not decorate @workflow.run with @traceable — it would violate
    # replay safety and produce duplicate or orphaned traces. Instead,
    # wrap an inner function.
    @workflow.run
    async def run(self, prompt: str) -> str:
        @traceable(
            name=f"Ask: {prompt[:60]}",
            run_type="chain",
            metadata={"workflow_id": workflow.info().workflow_id},
            tags=["basic-llm"],
        )
        async def _run() -> str:
            return await workflow.execute_activity(
                call_openai,
                OpenAIRequest(model="gpt-4o-mini", input=prompt),
                start_to_close_timeout=timedelta(seconds=60),
            )

        return await _run()
