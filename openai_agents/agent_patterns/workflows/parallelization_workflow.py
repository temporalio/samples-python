import asyncio

from agents import Agent, ItemHelpers, RunConfig, Runner, trace
from temporalio import workflow

"""
This example shows the parallelization pattern. We run the agent three times in parallel, and pick
the best result.

*Adapted from the OpenAI Agents SDK parallelization pattern example*
"""


def spanish_agent() -> Agent:
    return Agent(
        name="spanish_agent",
        instructions="You translate the user's message to Spanish",
    )


def translation_picker() -> Agent:
    return Agent(
        name="translation_picker",
        instructions="You pick the best Spanish translation from the given options.",
    )


@workflow.defn
class ParallelizationWorkflow:
    @workflow.run
    async def run(self, msg: str) -> str:
        config = RunConfig()

        # Ensure the entire workflow is a single trace
        with trace("Parallel translation"):
            # Run three translation agents in parallel
            res_1, res_2, res_3 = await asyncio.gather(
                Runner.run(
                    spanish_agent(),
                    msg,
                    run_config=config,
                ),
                Runner.run(
                    spanish_agent(),
                    msg,
                    run_config=config,
                ),
                Runner.run(
                    spanish_agent(),
                    msg,
                    run_config=config,
                ),
            )

            outputs = [
                ItemHelpers.text_message_outputs(res_1.new_items),
                ItemHelpers.text_message_outputs(res_2.new_items),
                ItemHelpers.text_message_outputs(res_3.new_items),
            ]

            translations = "\n\n".join(outputs)
            workflow.logger.info(f"Generated translations:\n{translations}")

            best_translation = await Runner.run(
                translation_picker(),
                f"Input: {msg}\n\nTranslations:\n{translations}",
                run_config=config,
            )

            return f"Best translation: {best_translation.final_output}"
