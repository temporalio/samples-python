from temporalio import workflow

from openai_agents.adapters.temporal_model_provider import TemporalModelProvider

with workflow.unsafe.imports_passed_through():
    from agents import Agent, ItemHelpers, MessageOutputItem, Runner, trace, RunConfig

"""
This example shows the agents-as-tools pattern. The frontline agent receives a user message and
then picks which agents to call, as tools. In this case, it picks from a set of translation
agents.
"""


def orchestrator_agent() -> Agent:
    spanish_agent = Agent(
        name="spanish_agent",
        instructions="You translate the user's message to Spanish",
        handoff_description="An english to spanish translator",
    )

    french_agent = Agent(
        name="french_agent",
        instructions="You translate the user's message to French",
        handoff_description="An english to french translator",
    )

    italian_agent = Agent(
        name="italian_agent",
        instructions="You translate the user's message to Italian",
        handoff_description="An english to italian translator",
    )

    orchestrator_agent = Agent(
        name="orchestrator_agent",
        instructions=(
            "You are a translation agent. You use the tools given to you to translate."
            "If asked for multiple translations, you call the relevant tools in order."
            "You never translate on your own, you always use the provided tools."
        ),
        tools=[
            spanish_agent.as_tool(
                tool_name="translate_to_spanish",
                tool_description="Translate the user's message to Spanish",
            ),
            french_agent.as_tool(
                tool_name="translate_to_french",
                tool_description="Translate the user's message to French",
            ),
            italian_agent.as_tool(
                tool_name="translate_to_italian",
                tool_description="Translate the user's message to Italian",
            ),
        ],
    )
    return orchestrator_agent


def synthesizer_agent() -> Agent:
    return Agent(
        name="synthesizer_agent",
        instructions="You inspect translations, correct them if needed, and produce a final concatenated response.",
    )


@workflow.defn(sandboxed=False)
class AgentsAsToolsWorkflow:
    @workflow.run
    async def run(self, msg: str) -> str:
        config = RunConfig(model_provider=TemporalModelProvider())

        # Run the entire orchestration in a single trace
        with trace("Orchestrator evaluator"):
            orchestrator = orchestrator_agent()
            synthesizer = synthesizer_agent()

            orchestrator_result = await Runner.run(orchestrator, msg, run_config=config)

            for item in orchestrator_result.new_items:
                if isinstance(item, MessageOutputItem):
                    text = ItemHelpers.text_message_output(item)
                    if text:
                        print(f"  - Translation step: {text}")

            synthesizer_result = await Runner.run(
                synthesizer, orchestrator_result.to_input_list(), run_config=config
            )

        return synthesizer_result.final_output
