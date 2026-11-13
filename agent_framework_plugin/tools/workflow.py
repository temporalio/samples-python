"""Two tool patterns on one agent: a pure tool in the Workflow and an Activity.

``letter_counter`` is plain logic, so it runs in the Workflow as an ordinary
``@tool``. ``fetch_weather`` stands in for an HTTP call, so it is an Activity
wrapped with ``activity_as_tool`` and gets its own timeout and retries.
"""

from datetime import timedelta
from typing import Any

from agent_framework import Agent, tool
from temporalio import activity, workflow
from temporalio.agent_framework import TemporalChatClient
from temporalio.agent_framework.workflow import activity_as_tool


# @@@SNIPSTART python-agent-framework-tools-tool
@tool
def letter_counter(word: str, letter: str) -> int:
    """Count how many times a letter appears in a word, ignoring case."""
    return word.lower().count(letter.lower())


# @@@SNIPEND


# @@@SNIPSTART python-agent-framework-tools-activity
@activity.defn
async def fetch_weather(city: str) -> dict[str, Any]:
    """Look up the current weather for a city."""
    # Stands in for an HTTP call. Anything that does I/O belongs in an Activity.
    return {"city": city, "temperature_f": 72, "conditions": "sunny"}


# @@@SNIPEND


# @@@SNIPSTART python-agent-framework-tools-workflow
@workflow.defn
class ToolsWorkflow:
    @workflow.run
    async def run(self, prompt: str) -> str:
        agent = Agent(
            client=TemporalChatClient(
                "gpt-4o-mini", start_to_close_timeout=timedelta(seconds=60)
            ),
            instructions="Use the tools you are given and answer briefly.",
            tools=[
                letter_counter,
                activity_as_tool(
                    fetch_weather, start_to_close_timeout=timedelta(seconds=30)
                ),
            ],
        )
        response = await agent.run(prompt)
        return response.text


# @@@SNIPEND
