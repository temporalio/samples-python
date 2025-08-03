from agents import Agent, RunConfig, Runner, TResponseInputItem, trace
from temporalio import workflow

"""
This example shows the handoffs/routing pattern. The triage agent receives the first message, and
then hands off to the appropriate agent based on the language of the request.

Note: This is adapted from the original streaming version to work with Temporal's non-streaming approach.

*Adapted from the OpenAI Agents SDK routing pattern example*
"""


def french_agent() -> Agent:
    return Agent(
        name="french_agent",
        instructions="You only speak French",
    )


def spanish_agent() -> Agent:
    return Agent(
        name="spanish_agent",
        instructions="You only speak Spanish",
    )


def english_agent() -> Agent:
    return Agent(
        name="english_agent",
        instructions="You only speak English",
    )


def triage_agent() -> Agent:
    return Agent(
        name="triage_agent",
        instructions="Handoff to the appropriate agent based on the language of the request.",
        handoffs=[french_agent(), spanish_agent(), english_agent()],
    )


@workflow.defn
class RoutingWorkflow:
    @workflow.run
    async def run(self, msg: str) -> str:
        config = RunConfig()

        with trace("Routing example"):
            inputs: list[TResponseInputItem] = [{"content": msg, "role": "user"}]

            # Run the triage agent to determine which language agent to handoff to
            result = await Runner.run(
                triage_agent(),
                input=inputs,
                run_config=config,
            )

            # Get the final response after handoff
            # Note: current_agent attribute may not be available in all SDK versions
            workflow.logger.info("Handoff completed")

            # Convert result to proper input format for next agent
            inputs = result.to_input_list()

            # Return the result from the handoff (either the handoff agent's response or triage response)
            return f"Response: {result.final_output}"
