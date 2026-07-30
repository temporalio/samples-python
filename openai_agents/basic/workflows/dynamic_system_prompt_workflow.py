from typing import Literal, Optional

from agents import Agent, RunContextWrapper, Runner
from temporalio import workflow


class CustomContext:
    def __init__(self, style: Literal["haiku", "pirate", "robot"]):
        self.style = style


def custom_instructions(
    run_context: RunContextWrapper[CustomContext], agent: Agent[CustomContext]
) -> str:
    context = run_context.context
    if context.style == "haiku":
        return "Only respond in haikus."
    elif context.style == "pirate":
        return "Respond as a pirate."
    else:
        return "Respond as a robot and say 'beep boop' a lot."


@workflow.defn
class DynamicSystemPromptWorkflow:
    @workflow.run
    async def run(self, user_message: str, style: Optional[str] = None) -> str:
        if style is None:
            selected_style: Literal["haiku", "pirate", "robot"] = (
                workflow.random().choice(["haiku", "pirate", "robot"])
            )
        else:
            # Validate that the provided style is one of the allowed values
            if style not in ["haiku", "pirate", "robot"]:
                raise ValueError(
                    f"Invalid style: {style}. Must be one of: haiku, pirate, robot"
                )
            selected_style = style  # type: ignore

        context = CustomContext(style=selected_style)

        agent = Agent(
            name="Chat agent",
            instructions=custom_instructions,
        )

        result = await Runner.run(agent, user_message, context=context)
        return f"Style: {selected_style}\nResponse: {result.final_output}"
