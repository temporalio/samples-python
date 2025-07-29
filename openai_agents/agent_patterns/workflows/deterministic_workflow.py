from agents import Agent, RunConfig, Runner, trace
from pydantic import BaseModel
from temporalio import workflow

"""
This example demonstrates a deterministic flow, where each step is performed by an agent.
1. The first agent generates a story outline
2. We feed the outline into the second agent
3. The second agent checks if the outline is good quality and if it is a scifi story
4. If the outline is not good quality or not a scifi story, we stop here
5. If the outline is good quality and a scifi story, we feed the outline into the third agent
6. The third agent writes the story

*Adapted from the OpenAI Agents SDK deterministic pattern example*
"""


class OutlineCheckerOutput(BaseModel):
    good_quality: bool
    is_scifi: bool


def story_outline_agent() -> Agent:
    return Agent(
        name="story_outline_agent",
        instructions="Generate a very short story outline based on the user's input.",
    )


def outline_checker_agent() -> Agent:
    return Agent(
        name="outline_checker_agent",
        instructions="Read the given story outline, and judge the quality. Also, determine if it is a scifi story.",
        output_type=OutlineCheckerOutput,
    )


def story_agent() -> Agent:
    return Agent(
        name="story_agent",
        instructions="Write a short story based on the given outline.",
        output_type=str,
    )


@workflow.defn
class DeterministicWorkflow:
    @workflow.run
    async def run(self, input_prompt: str) -> str:
        config = RunConfig()

        # Ensure the entire workflow is a single trace
        with trace("Deterministic story flow"):
            # 1. Generate an outline
            outline_result = await Runner.run(
                story_outline_agent(),
                input_prompt,
                run_config=config,
            )
            workflow.logger.info("Outline generated")

            # 2. Check the outline
            outline_checker_result = await Runner.run(
                outline_checker_agent(),
                outline_result.final_output,
                run_config=config,
            )

            # 3. Add a gate to stop if the outline is not good quality or not a scifi story
            assert isinstance(outline_checker_result.final_output, OutlineCheckerOutput)
            if not outline_checker_result.final_output.good_quality:
                workflow.logger.info("Outline is not good quality, so we stop here.")
                return "Story generation stopped: Outline quality insufficient."

            if not outline_checker_result.final_output.is_scifi:
                workflow.logger.info("Outline is not a scifi story, so we stop here.")
                return "Story generation stopped: Outline is not science fiction."

            workflow.logger.info(
                "Outline is good quality and a scifi story, so we continue to write the story."
            )

            # 4. Write the story
            story_result = await Runner.run(
                story_agent(),
                outline_result.final_output,
                run_config=config,
            )

            return f"Final story: {story_result.final_output}"
