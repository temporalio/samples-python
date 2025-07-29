from agents import (
    Agent,
    GuardrailFunctionOutput,
    InputGuardrailTripwireTriggered,
    RunConfig,
    RunContextWrapper,
    Runner,
    TResponseInputItem,
    input_guardrail,
)
from pydantic import BaseModel
from temporalio import workflow

"""
This example shows how to use input guardrails.

Guardrails are checks that run in parallel to the agent's execution.
They can be used to do things like:
- Check if input messages are off-topic
- Check that input messages don't violate any policies
- Take over control of the agent's execution if an unexpected input is detected

In this example, we'll setup an input guardrail that trips if the user is asking to do math homework.
If the guardrail trips, we'll respond with a refusal message.

*Adapted from the OpenAI Agents SDK input_guardrails pattern example*
"""


class MathHomeworkOutput(BaseModel):
    reasoning: str
    is_math_homework: bool


guardrail_agent = Agent(
    name="Guardrail check",
    instructions="Check if the user is asking you to do their math homework.",
    output_type=MathHomeworkOutput,
)


@input_guardrail
async def math_guardrail(
    context: RunContextWrapper[None],
    agent: Agent,
    input: str | list[TResponseInputItem],
) -> GuardrailFunctionOutput:
    """This is an input guardrail function, which happens to call an agent to check if the input
    is a math homework question.
    """
    result = await Runner.run(guardrail_agent, input, context=context.context)
    final_output = result.final_output_as(MathHomeworkOutput)

    return GuardrailFunctionOutput(
        output_info=final_output,
        tripwire_triggered=final_output.is_math_homework,
    )


@workflow.defn
class InputGuardrailsWorkflow:
    @workflow.run
    async def run(self, user_input: str) -> str:
        config = RunConfig()
        agent = Agent(
            name="Customer support agent",
            instructions="You are a customer support agent. You help customers with their questions.",
            input_guardrails=[math_guardrail],
        )

        input_data: list[TResponseInputItem] = [
            {
                "role": "user",
                "content": user_input,
            }
        ]

        try:
            result = await Runner.run(agent, input_data, run_config=config)
            return str(result.final_output)
        except InputGuardrailTripwireTriggered:
            # If the guardrail triggered, we instead return a refusal message
            message = "Sorry, I can't help you with your math homework."
            workflow.logger.info(
                "Input guardrail triggered - refusing to help with math homework"
            )
            return message
