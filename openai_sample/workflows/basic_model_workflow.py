from __future__ import annotations

from datetime import timedelta

from temporalio import workflow

from openai_sample.activities.basic_model_activity import basic_model_invocation

with workflow.unsafe.imports_passed_through():
    from braintrust import traced, init_logger

logger=init_logger(project="Temporal-first-project")

@workflow.defn(sandboxed=False)
class BasicModelWorkflow:
    @traced
    @workflow.run
    async def run(self, question: str) -> str:
        return await self.do_model(question)

    @traced
    async def do_model(self, question: str) -> str:
        return await workflow.execute_activity(
            basic_model_invocation,
            question,
            start_to_close_timeout=timedelta(minutes=1),
        )