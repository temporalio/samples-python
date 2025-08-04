from typing import Any, Literal

from agents import (
    Agent,
    FunctionToolResult,
    ModelSettings,
    RunConfig,
    RunContextWrapper,
    Runner,
    ToolsToFinalOutputFunction,
    ToolsToFinalOutputResult,
    function_tool,
)
from pydantic import BaseModel
from temporalio import workflow

"""
This example shows how to force the agent to use a tool. It uses `ModelSettings(tool_choice="required")`
to force the agent to use any tool.

You can run it with 3 options:
1. `default`: The default behavior, which is to send the tool output to the LLM. In this case,
    `tool_choice` is not set, because otherwise it would result in an infinite loop - the LLM would
    call the tool, the tool would run and send the results to the LLM, and that would repeat
    (because the model is forced to use a tool every time.)
2. `first_tool_result`: The first tool result is used as the final output.
3. `custom`: A custom tool use behavior function is used. The custom function receives all the tool
    results, and chooses to use the first tool result to generate the final output.

*Adapted from the OpenAI Agents SDK forcing_tool_use pattern example*
"""


class Weather(BaseModel):
    city: str
    temperature_range: str
    conditions: str


@function_tool
def get_weather(city: str) -> Weather:
    workflow.logger.info("[debug] get_weather called")
    return Weather(city=city, temperature_range="14-20C", conditions="Sunny with wind")


async def custom_tool_use_behavior(
    context: RunContextWrapper[Any], results: list[FunctionToolResult]
) -> ToolsToFinalOutputResult:
    weather: Weather = results[0].output
    return ToolsToFinalOutputResult(
        is_final_output=True, final_output=f"{weather.city} is {weather.conditions}."
    )


@workflow.defn
class ForcingToolUseWorkflow:
    @workflow.run
    async def run(self, tool_use_behavior: str = "default") -> str:
        config = RunConfig()

        if tool_use_behavior == "default":
            behavior: Literal[
                "run_llm_again", "stop_on_first_tool"
            ] | ToolsToFinalOutputFunction = "run_llm_again"
        elif tool_use_behavior == "first_tool":
            behavior = "stop_on_first_tool"
        elif tool_use_behavior == "custom":
            behavior = custom_tool_use_behavior

        agent = Agent(
            name="Weather agent",
            instructions="You are a helpful agent.",
            tools=[get_weather],
            tool_use_behavior=behavior,
            model_settings=ModelSettings(
                tool_choice="required" if tool_use_behavior != "default" else None
            ),
        )

        result = await Runner.run(
            agent, input="What's the weather in Tokyo?", run_config=config
        )
        return str(result.final_output)
