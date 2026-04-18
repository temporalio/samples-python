"""LangSmith tracing with LangGraph Graph API and Temporal.

Demonstrates combining LangGraphPlugin (durable graph execution) with
LangSmithPlugin (observability) for full tracing of LLM calls through
Temporal workflows.

Requires ANTHROPIC_API_KEY and LANGCHAIN_API_KEY environment variables.
"""

from datetime import timedelta

from langgraph.graph import START, StateGraph
from langsmith import traceable
from temporalio import workflow

from langchain.chat_models import init_chat_model


@traceable(name="chat_activity", run_type="chain")
async def chat(message: str) -> str:
    """Call an LLM to respond to the message. Traced by LangSmith."""
    response = await init_chat_model("claude-sonnet-4-6").ainvoke(message)
    return response.content


chat_graph = StateGraph(str)
chat_graph.add_node(
    "chat",
    chat,
    metadata={"start_to_close_timeout": timedelta(seconds=30)},
)
chat_graph.add_edge(START, "chat")


@workflow.defn
class ChatWorkflow:
    @workflow.run
    async def run(self, message: str) -> str:
        return await chat_graph.compile().ainvoke(message)
