"""Three tool patterns wired into one Strands agent.

1. ``@tool letter_counter`` — pure Strands tool, runs deterministically in
   workflow context.
2. ``@activity.defn fetch_weather`` — custom Temporal activity wrapped with
   ``activity_as_tool``; suitable for I/O and non-deterministic work.
3. ``shell`` (from ``strands_tools``) — third-party Strands tool wrapped in a
   thin ``@activity.defn`` so its subprocess execution runs in an activity.
"""

from datetime import timedelta

from strands import tool
from strands_tools import shell  # type: ignore[import-untyped]
from temporalio import activity, workflow
from temporalio.contrib.strands import TemporalAgent
from temporalio.contrib.strands.workflow import activity_as_tool


@tool
def letter_counter(word: str, letter: str) -> int:
    """Count how many times ``letter`` appears in ``word`` (case-insensitive)."""
    return word.lower().count(letter.lower())


@activity.defn
async def fetch_weather(city: str) -> dict:
    """Stub weather lookup — replace with a real HTTP call in production."""
    return {
        "city": city,
        "temperature_f": 72,
        "conditions": "sunny",
    }


@activity.defn(name="shell")
async def shell_activity(command: str) -> dict:
    """Run ``strands_tools.shell`` inside an activity.

    ``strands_tools`` ships sync tools that shell out and read files; wrapping
    them in an activity keeps the workflow itself deterministic.
    """
    return shell.shell(command=command, non_interactive=True)


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
                    shell_activity,
                    start_to_close_timeout=timedelta(seconds=30),
                ),
            ],
        )

    @workflow.run
    async def run(self, prompt: str) -> str:
        result = await self.agent.invoke_async(prompt)
        return str(result)
