from typing import Tuple

from agents import Agent, Runner
from temporalio import workflow


@workflow.defn
class PreviousResponseIdWorkflow:
    @workflow.run
    async def run(
        self, first_question: str, follow_up_question: str
    ) -> Tuple[str, str]:
        """
        Demonstrates usage of the `previous_response_id` parameter to continue a conversation.
        The second run passes the previous response ID to the model, which allows it to continue the
        conversation without re-sending the previous messages.

        Notes:
        1. This only applies to the OpenAI Responses API. Other models will ignore this parameter.
        2. Responses are only stored for 30 days as of this writing, so in production you should
        store the response ID along with an expiration date; if the response is no longer valid,
        you'll need to re-send the previous conversation history.

        Args:
            first_question: The initial question to ask
            follow_up_question: The follow-up question that references the first response

        Returns:
            Tuple of (first_response, second_response)
        """
        agent = Agent(
            name="Assistant",
            instructions="You are a helpful assistant. be VERY concise.",
        )

        # First question
        result1 = await Runner.run(agent, first_question)
        first_response = result1.final_output

        # Follow-up question using previous response ID
        result2 = await Runner.run(
            agent,
            follow_up_question,
            previous_response_id=result1.last_response_id,
        )
        second_response = result2.final_output

        return first_response, second_response
