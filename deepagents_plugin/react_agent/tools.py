"""Tools for the react agent sample.

``tool_as_activity(...)`` registers the tool in the worker process, so call it
here at module level and import this module in the workflow file under
``workflow.unsafe.imports_passed_through()``. Calling it inside the workflow
registers the tool only once a run gets there, and a worker that has not run
the workflow yet fails the tool activity.
"""

# @@@SNIPSTART python-deepagents-react-agent-activity
from datetime import timedelta

from langchain_core.tools import tool
from temporalio import activity
from temporalio.deepagents import activity_as_tool, tool_as_activity
from temporalio.workflow import ActivityConfig


@activity.defn
async def get_weather(city: str) -> str:
    """Return the current weather for a city."""
    # A real implementation would call a weather API here; this is a stand-in.
    return f"It is sunny and 22C in {city}."


@tool
def web_search(query: str) -> str:
    """Search the web for a query and return a short result."""
    # Real I/O (an HTTP call) would go here; wrapped with tool_as_activity so it
    # runs in an activity, not in workflow code.
    return f"Top result for {query!r}: Temporal makes code durable."


# An existing Temporal activity, exposed to the agent as a tool.
weather_tool = activity_as_tool(
    get_weather,
    activity_options=ActivityConfig(start_to_close_timeout=timedelta(seconds=30)),
)
# A LangChain tool whose body does I/O, moved into an activity.
search_tool = tool_as_activity(web_search, start_to_close_timeout=timedelta(seconds=30))


# @@@SNIPEND
