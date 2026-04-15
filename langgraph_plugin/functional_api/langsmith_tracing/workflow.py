"""LangSmith tracing with LangGraph Functional API and Temporal.

Demonstrates combining LangGraphPlugin (durable task execution) with
LangSmithPlugin (observability) for full tracing of LLM calls through
Temporal workflows.

Requires ANTHROPIC_API_KEY and LANGCHAIN_API_KEY environment variables.
"""

from datetime import timedelta

from langgraph.func import entrypoint as lg_entrypoint
from langgraph.func import task
from langsmith import traceable
from temporalio import workflow
from temporalio.contrib.langgraph import entrypoint

from langchain.chat_models import init_chat_model


@task
@traceable(name="chat_task", run_type="chain")
def chat(message: str) -> str:
    """Call an LLM to respond to the message. Traced by LangSmith."""
    response = init_chat_model("claude-sonnet-4-6").invoke(message)
    return response.content


@lg_entrypoint()
async def chat_entrypoint(message: str) -> dict:
    """Chat entrypoint: call the LLM and return the response."""
    response = await chat(message)
    return {"response": response}


all_tasks = [chat]

activity_options = {
    t.func.__name__: {"start_to_close_timeout": timedelta(seconds=30)}
    for t in all_tasks
}


@workflow.defn
class ChatFunctionalWorkflow:
    @workflow.run
    async def run(self, message: str) -> dict:
        return await entrypoint("chat").ainvoke(message)
