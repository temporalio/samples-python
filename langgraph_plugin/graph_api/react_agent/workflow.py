"""ReAct agent using the LangGraph Graph API with Temporal.

Demonstrates the most common LangGraph pattern: a tool-calling agent that loops
between "thinking" (deciding the next action) and "acting" (executing a tool),
using conditional edges to control the loop.

Graph topology:
  START -> agent -> (tools -> agent)* -> END
"""

import operator
from datetime import timedelta
from typing import Annotated, Any, TypedDict

from langgraph.graph import END, START, StateGraph
from temporalio import workflow
from temporalio.contrib.langgraph import graph


class AgentState(TypedDict):
    """State for the ReAct agent.

    'messages' uses operator.add so each node appends to the list rather
    than replacing it, accumulating the full conversation history.
    """

    input: str
    messages: Annotated[list[str], operator.add]
    final_answer: str


async def agent(state: AgentState) -> dict[str, Any]:
    """The agent decides what to do next based on the conversation history.

    In production, replace this with an LLM call (e.g., Claude with tools).
    This stub simulates a 2-step research process.
    """
    messages = state.get("messages", [])
    tool_results = [m for m in messages if m.startswith("[Tool]")]

    if len(tool_results) == 0:
        return {
            "messages": [
                "[Agent] I need weather data. Calling get_weather for San Francisco."
            ]
        }
    elif len(tool_results) == 1:
        return {
            "messages": [
                "[Agent] Now I need population data. "
                "Calling get_population for San Francisco."
            ]
        }
    else:
        facts = "; ".join(tool_results)
        return {
            "messages": ["[Agent] I have all the information I need."],
            "final_answer": (f"Here's what I found about San Francisco: {facts}"),
        }


async def tools(state: AgentState) -> dict[str, Any]:
    """Execute the tool requested by the agent."""
    last_msg = state["messages"][-1]

    if "get_weather" in last_msg:
        return {"messages": ["[Tool] Weather in San Francisco: 72°F and sunny."]}
    elif "get_population" in last_msg:
        return {"messages": ["[Tool] San Francisco population: ~870,000 residents."]}
    else:
        return {"messages": ["[Tool] Unknown tool requested."]}


async def should_continue(state: AgentState) -> str:
    """Route: if the agent requested a tool, go to 'tools'. Otherwise, end.

    Must be async to avoid run_in_executor inside Temporal's workflow sandbox.
    """
    last_msg = state["messages"][-1]
    if last_msg.startswith("[Agent]") and "Calling" in last_msg:
        return "tools"
    return END


def build_graph() -> StateGraph:
    """Construct the ReAct agent graph with conditional edges."""
    timeout = {"start_to_close_timeout": timedelta(seconds=30)}
    g = StateGraph(AgentState)
    g.add_node("agent", agent, metadata=timeout)
    g.add_node("tools", tools, metadata=timeout)
    g.add_edge(START, "agent")
    g.add_conditional_edges("agent", should_continue)
    g.add_edge("tools", "agent")
    return g


@workflow.defn
class ReactAgentWorkflow:
    @workflow.run
    async def run(self, query: str) -> str:
        initial_state: AgentState = {
            "input": query,
            "messages": [],
            "final_answer": "",
        }
        result = await graph("react-agent").compile().ainvoke(initial_state)
        return result["final_answer"]
