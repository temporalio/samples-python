"""Three tool patterns wired into one Strands agent.

1. ``@tool letter_counter`` — pure Strands tool, runs deterministically in
   workflow context.
2. ``@activity.defn fetch_weather`` — custom Temporal activity wrapped with
   ``activity_as_tool``; suitable for I/O and non-deterministic work.
3. ``environment`` (from ``strands_tools``) — third-party Strands tool wrapped
   in a thin ``@activity.defn`` so its runtime host access runs in an activity.
"""

from datetime import timedelta
from typing import Any, cast

from strands import tool
from strands.types.tools import ToolUse
from strands_tools import environment  # type: ignore[import-untyped]
from temporalio import activity, workflow
from temporalio.contrib.strands import TemporalAgent
from temporalio.contrib.strands.workflow import activity_as_tool


@tool
def letter_counter(word: str, letter: str) -> int:
    """Count how many times ``letter`` appears in ``word`` (case-insensitive)."""
    return word.lower().count(letter.lower())


# @@@SNIPSTART python-strands-tools-activity
@activity.defn
async def fetch_weather(city: str) -> dict:
    """Stub weather lookup — replace with a real HTTP call in production."""
    return {
        "city": city,
        "temperature_f": 72,
        "conditions": "sunny",
    }
# @@@SNIPEND


@activity.defn(name="environment")
async def environment_activity(
    action: str,
    name: str | None = None,
    value: str | None = None,
    prefix: str | None = None,
    masked: bool | None = None,
) -> dict:
    """Run ``strands_tools.environment`` inside an activity.

    Environment variables are runtime host state. Wrapping this tool in an
    activity keeps that non-deterministic access out of workflow replay.
    """
    tool_input: dict[str, Any] = {"action": action}
    if name is not None:
        tool_input["name"] = name
    if value is not None:
        tool_input["value"] = value
    if prefix is not None:
        tool_input["prefix"] = prefix
    if masked is not None:
        tool_input["masked"] = masked

    tool_use = cast(
        ToolUse,
        {
            "toolUseId": "environment",
            "name": "environment",
            "input": tool_input,
        },
    )
    return environment.environment(tool_use)


# @@@SNIPSTART python-strands-tools-workflow
@workflow.defn
class ToolsWorkflow:
    def __init__(self) -> None:
        self.agent = TemporalAgent(
            start_to_close_timeout=timedelta(seconds=60),
            tools=[
                letter_counter,
                activity_as_tool(
                    fetch_weather,
                    start_to_close_timeout=timedelta(seconds=30),
                ),
                activity_as_tool(
                    environment_activity,
                    start_to_close_timeout=timedelta(seconds=30),
                ),
            ],
        )

    @workflow.run
    async def run(self, prompt: str) -> str:
        result = await self.agent.invoke_async(prompt)
        return str(result)
# @@@SNIPEND
