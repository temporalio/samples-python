"""Tool-calling Deep Agent: the explicit Workflow-vs-Activity choice per tool.

A Deep Agent holds its tools in-workflow. A tool that only reads/writes agent
state is pure and belongs there; a tool that does real I/O must not run in
workflow code. This sample shows the two explicit ways to move a tool's work to
an activity:

* ``activity_as_tool`` — surface an existing ``@activity.defn`` (``get_weather``)
  as a Deep Agents tool. Temporal adopters already have activities; they should
  not have to re-declare them.
* ``tool_as_activity`` — wrap a LangChain tool (``web_search``) whose body does
  I/O so its execution runs as a ``deepagents.invoke_tool`` activity.

The model is constructed explicitly as ``TemporalModel(...)`` to show the
non-auto path (the plugin would otherwise wrap a bare ``model=`` string for you).
Every model turn and every tool call in the loop is a durable activity.
"""

from datetime import timedelta

from temporalio import activity, workflow

with workflow.unsafe.imports_passed_through():
    from deepagents import create_deep_agent
    from langchain_core.tools import tool
    from temporalio.contrib.deepagents import (
        TemporalModel,
        activity_as_tool,
        tool_as_activity,
    )


# @@@SNIPSTART python-deepagents-react-agent-activity
@activity.defn
async def get_weather(city: str) -> str:
    """Return the current weather for a city."""
    # A real implementation would call a weather API here; this is a stand-in.
    return f"It is sunny and 22C in {city}."


# @@@SNIPEND


# @@@SNIPSTART python-deepagents-react-agent-workflow
@tool
def web_search(query: str) -> str:
    """Search the web for a query and return a short result."""
    # Real I/O (an HTTP call) would go here; wrapped with tool_as_activity so it
    # runs in an activity, not in workflow code.
    return f"Top result for {query!r}: Temporal makes code durable."


@workflow.defn
class ReactAgent:
    @workflow.run
    async def run(self, question: str) -> str:
        weather_tool = activity_as_tool(
            get_weather,
            start_to_close_timeout=timedelta(seconds=30),
        )
        search_tool = tool_as_activity(
            web_search,
            start_to_close_timeout=timedelta(seconds=30),
        )
        agent = create_deep_agent(
            model=TemporalModel(model="anthropic:claude-sonnet-4-5"),
            tools=[weather_tool, search_tool],
            system_prompt=(
                "You are a research assistant. Use the get_weather and "
                "web_search tools when they help answer the question."
            ),
        )
        result = await agent.ainvoke(
            {"messages": [{"role": "user", "content": question}]}
        )
        return result["messages"][-1].content


# @@@SNIPEND
