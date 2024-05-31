from datetime import timedelta
from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from activities import prompt_bedrock


@workflow.defn
class SimpleBedrockWorkflow:
    @workflow.run
    async def run(self, prompt: str) -> str:

        workflow.logger.info("Prompt: %s" % prompt)

        response = await workflow.execute_activity(
            prompt_bedrock, prompt,
            schedule_to_close_timeout=timedelta(seconds=20)
        )

        workflow.logger.info("Response: %s" % response)

        return response
