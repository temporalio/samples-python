"""LangSmith tracing with LangGraph Graph API and Temporal.

Demonstrates combining LangGraphPlugin (durable graph execution) with
LangSmithPlugin (observability) for full tracing of LLM calls through
Temporal workflows.

Three @traceable use cases are demonstrated:
1. The Activity (graph node) function itself: `chat`.
2. A helper called from inside the Activity: `format_prompt`.
3. A helper called from inside the Workflow: `summarize_for_log`.

Requires ANTHROPIC_API_KEY and LANGCHAIN_API_KEY environment variables.
"""

from datetime import timedelta

from langchain.chat_models import init_chat_model
from langgraph.graph import START, StateGraph
from langsmith import traceable
from temporalio import workflow
from temporalio.contrib.langgraph import graph as temporal_graph
from typing_extensions import TypedDict


class State(TypedDict):
    value: str


@traceable(name="format_prompt", run_type="prompt")
def format_prompt(message: str) -> str:
    """Helper called from inside the Activity. Traced by LangSmith."""
    return f"Please respond concisely to: {message}"


@traceable(name="chat_activity", run_type="chain")
async def chat(state: State) -> dict[str, str]:
    """Call an LLM to respond to the message. Traced by LangSmith."""
    prompt = format_prompt(state["value"])
    response = await init_chat_model("claude-sonnet-4-6").ainvoke(prompt)
    return {"value": str(response.content)}


@traceable(name="summarize_for_log", run_type="chain")
def summarize_for_log(response: str) -> str:
    """Helper called from inside the Workflow. Traced by LangSmith."""
    return f"Got {len(response)}-char response: {response[:60]}..."


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
        result = await temporal_graph("chat").compile().ainvoke({"value": message})
        response = result["value"]
        workflow.logger.info(summarize_for_log(response))
        return response
