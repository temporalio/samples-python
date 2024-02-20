from datetime import timedelta

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from activities import TranslateParams, translate_phrase


@workflow.defn
class LangChainWorkflow:
    @workflow.run
    async def run(self, params: TranslateParams) -> dict:
        return await workflow.execute_activity(
            translate_phrase,
            params,
            schedule_to_close_timeout=timedelta(seconds=30),
        )
