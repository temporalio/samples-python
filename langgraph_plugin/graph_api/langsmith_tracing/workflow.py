"""LangSmith tracing with LangGraph Graph API and Temporal.

Demonstrates combining LangGraphPlugin (durable graph execution) with
LangSmithPlugin (observability) for full tracing of LLM calls through
Temporal workflows.

Requires ANTHROPIC_API_KEY and LANGCHAIN_API_KEY environment variables.
"""

from datetime import timedelta

from langchain.chat_models import init_chat_model
from langgraph.graph import START, StateGraph
from langsmith import traceable
from temporalio import workflow
from temporalio.contrib.langgraph import graph
from typing_extensions import TypedDict


class State(TypedDict):
    value: str


@traceable(name="chat_activity", run_type="chain")
async def chat(state: State) -> dict[str, str]:
    """Call an LLM to respond to the message. Traced by LangSmith."""
    response = await init_chat_model("claude-sonnet-4-6").ainvoke(state["value"])
    return {"value": str(response.content)}


def make_chat_graph() -> StateGraph:
    g = StateGraph(State)
    g.add_node(
        "chat",
        chat,
        metadata={
            "execute_in": "activity",
            "start_to_close_timeout": timedelta(seconds=30),
        },
    )
    g.add_edge(START, "chat")
    return g


@workflow.defn
class ChatWorkflow:
    @workflow.run
    async def run(self, message: str) -> str:
        result = await graph("chat").compile().ainvoke({"value": message})
        return result["value"]
