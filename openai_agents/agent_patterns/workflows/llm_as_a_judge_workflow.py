from dataclasses import dataclass
from typing import Literal

from agents import Agent, ItemHelpers, RunConfig, Runner, TResponseInputItem, trace
from temporalio import workflow

"""
This example shows the LLM as a judge pattern. The first agent generates an outline for a story.
The second agent judges the outline and provides feedback. We loop until the judge is satisfied
with the outline.

*Adapted from the OpenAI Agents SDK llm_as_a_judge pattern example*
"""


@dataclass
class EvaluationFeedback:
    feedback: str
    score: Literal["pass", "needs_improvement", "fail"]


def story_outline_generator() -> Agent:
    return Agent[None](
        name="story_outline_generator",
        instructions=(
            "You generate a very short story outline based on the user's input."
            "If there is any feedback provided, use it to improve the outline."
        ),
    )


def evaluator() -> Agent:
    return Agent[None](
        name="evaluator",
        instructions=(
            "You evaluate a story outline and decide if it's good enough."
            "If it's not good enough, you provide feedback on what needs to be improved."
            "Never give it a pass on the first try. After 5 attempts, you can give it a pass if story outline is good enough - do not go for perfection"
        ),
        output_type=EvaluationFeedback,
    )


@workflow.defn
class LLMAsAJudgeWorkflow:
    @workflow.run
    async def run(self, msg: str) -> str:
        config = RunConfig()
        input_items: list[TResponseInputItem] = [{"content": msg, "role": "user"}]
        latest_outline: str | None = None

        # We'll run the entire workflow in a single trace
        with trace("LLM as a judge"):
            while True:
                story_outline_result = await Runner.run(
                    story_outline_generator(),
                    input_items,
                    run_config=config,
                )

                input_items = story_outline_result.to_input_list()
                latest_outline = ItemHelpers.text_message_outputs(
                    story_outline_result.new_items
                )
                workflow.logger.info("Story outline generated")

                evaluator_result = await Runner.run(
                    evaluator(),
                    input_items,
                    run_config=config,
                )
                result: EvaluationFeedback = evaluator_result.final_output

                workflow.logger.info(f"Evaluator score: {result.score}")

                if result.score == "pass":
                    workflow.logger.info("Story outline is good enough, exiting.")
                    break

                workflow.logger.info("Re-running with feedback")

                input_items.append(
                    {"content": f"Feedback: {result.feedback}", "role": "user"}
                )

        return f"Final story outline: {latest_outline}"
