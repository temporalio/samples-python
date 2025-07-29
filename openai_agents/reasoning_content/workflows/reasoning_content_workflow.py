from dataclasses import dataclass

from temporalio import workflow

from openai_agents.reasoning_content.activities.reasoning_activities import (
    get_reasoning_response,
)


@dataclass
class ReasoningResult:
    reasoning_content: str | None
    regular_content: str | None
    prompt: str


@workflow.defn
class ReasoningContentWorkflow:
    @workflow.run
    async def run(self, prompt: str, model_name: str | None = None) -> ReasoningResult:
        # Call the activity to get the reasoning response
        reasoning_content, regular_content = await workflow.execute_activity(
            get_reasoning_response,
            args=[prompt, model_name],
            start_to_close_timeout=workflow.timedelta(minutes=5),
        )

        return ReasoningResult(
            reasoning_content=reasoning_content,
            regular_content=regular_content,
            prompt=prompt,
        )
