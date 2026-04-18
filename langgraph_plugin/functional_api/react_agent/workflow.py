"""ReAct agent using the LangGraph Functional API with Temporal.

Same pattern as the Graph API version, but using @task and @entrypoint.
The Functional API naturally expresses the ReAct loop as a while loop,
making the control flow explicit and easy to extend.
"""

from datetime import timedelta

from langgraph.func import entrypoint as lg_entrypoint
from langgraph.func import task
from temporalio import workflow


@task
def agent_think(query: str, history: list[str]) -> dict:
    """The agent decides the next action based on query and tool history.

    In production, replace this with an LLM call (e.g., Claude with tools).
    """
    tool_results = [h for h in history if h.startswith("[Tool]")]

    if len(tool_results) == 0:
        return {
            "action": "tool",
            "tool_name": "get_weather",
            "tool_input": "San Francisco",
        }
    elif len(tool_results) == 1:
        return {
            "action": "tool",
            "tool_name": "get_population",
            "tool_input": "San Francisco",
        }
    else:
        facts = "; ".join(tool_results)
        return {
            "action": "final",
            "answer": (f"Here's what I found about San Francisco: {facts}"),
        }


@task
def execute_tool(tool_name: str, tool_input: str) -> str:
    """Execute a tool by name. In production, dispatch to real implementations."""
    tool_registry = {
        "get_weather": lambda inp: f"[Tool] Weather in {inp}: 72°F and sunny.",
        "get_population": lambda inp: f"[Tool] {inp} population: ~870,000 residents.",
    }
    handler = tool_registry.get(tool_name)
    if handler:
        return handler(tool_input)
    return f"[Tool] Unknown tool: {tool_name}"


@lg_entrypoint()
async def react_agent_entrypoint(query: str) -> dict:
    """ReAct agent loop: think -> act -> observe -> repeat."""
    history: list[str] = []

    while True:
        decision = await agent_think(query, history)

        if decision["action"] == "final":
            return {"answer": decision["answer"], "steps": len(history)}

        result = await execute_tool(decision["tool_name"], decision["tool_input"])
        history.append(result)


all_tasks = [agent_think, execute_tool]

activity_options = {
    t.func.__name__: {"start_to_close_timeout": timedelta(seconds=30)}
    for t in all_tasks
}


@workflow.defn
class ReactAgentFunctionalWorkflow:
    @workflow.run
    async def run(self, query: str) -> dict:
        return await react_agent_entrypoint.ainvoke(query)
