from agents import (
    Agent,
    GuardrailFunctionOutput,
    OutputGuardrailTripwireTriggered,
    RunConfig,
    RunContextWrapper,
    Runner,
    output_guardrail,
)
from pydantic import BaseModel, Field
from temporalio import workflow

"""
This example shows how to use output guardrails.

Output guardrails are checks that run on the final output of an agent.
They can be used to do things like:
- Check if the output contains sensitive data
- Check if the output is a valid response to the user's message

In this example, we'll use a (contrived) example where we check if the agent's response contains
a phone number.

*Adapted from the OpenAI Agents SDK output_guardrails pattern example*
"""


class MessageOutput(BaseModel):
    reasoning: str = Field(
        description="Thoughts on how to respond to the user's message"
    )
    response: str = Field(description="The response to the user's message")
    user_name: str | None = Field(
        description="The name of the user who sent the message, if known"
    )


@output_guardrail
async def sensitive_data_check(
    context: RunContextWrapper, agent: Agent, output: MessageOutput
) -> GuardrailFunctionOutput:
    phone_number_in_response = "650" in output.response
    phone_number_in_reasoning = "650" in output.reasoning

    return GuardrailFunctionOutput(
        output_info={
            "phone_number_in_response": phone_number_in_response,
            "phone_number_in_reasoning": phone_number_in_reasoning,
        },
        tripwire_triggered=phone_number_in_response or phone_number_in_reasoning,
    )


def assistant_agent() -> Agent:
    return Agent(
        name="Assistant",
        instructions="You are a helpful assistant.",
        output_type=MessageOutput,
        output_guardrails=[sensitive_data_check],
    )


@workflow.defn
class OutputGuardrailsWorkflow:
    @workflow.run
    async def run(self, user_input: str) -> str:
        config = RunConfig()
        agent = assistant_agent()

        try:
            result = await Runner.run(agent, user_input, run_config=config)
            output = result.final_output_as(MessageOutput)
            return f"Response: {output.response}"
        except OutputGuardrailTripwireTriggered as e:
            workflow.logger.info(
                f"Output guardrail triggered. Info: {e.guardrail_result.output.output_info}"
            )
            return f"Output guardrail triggered due to sensitive data detection. Info: {e.guardrail_result.output.output_info}"
