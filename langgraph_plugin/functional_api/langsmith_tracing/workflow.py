"""LangSmith tracing with LangGraph Functional API and Temporal.

Demonstrates combining LangGraphPlugin (durable task execution) with
LangSmithPlugin (observability) for full tracing of LLM calls through
Temporal workflows.

Three @traceable use cases are demonstrated:
1. The @task (Activity) function itself: `chat`.
2. A helper called from inside the @task: `format_prompt`.
3. A helper called from inside the @entrypoint (Workflow): `summarize_for_log`.

Requires ANTHROPIC_API_KEY and LANGCHAIN_API_KEY environment variables.
"""

from datetime import timedelta

from langchain.chat_models import init_chat_model
from langgraph.func import entrypoint, task
from langsmith import traceable
from temporalio import workflow
from temporalio.contrib.langgraph import entrypoint as temporal_entrypoint


@traceable(name="format_prompt", run_type="prompt")
def format_prompt(message: str) -> str:
    """Helper called from inside the @task. Traced by LangSmith."""
    return f"Please respond concisely to: {message}"


@task
@traceable(name="chat_task", run_type="chain")
def chat(message: str) -> str:
    """Call an LLM to respond to the message. Traced by LangSmith."""
    prompt = format_prompt(message)
    response = init_chat_model("claude-sonnet-4-6").invoke(prompt)
    return str(response.content)


@traceable(name="summarize_for_log", run_type="chain")
def summarize_for_log(response: str) -> str:
    """Helper called from inside the @entrypoint. Traced by LangSmith."""
    return f"Got {len(response)}-char response: {response[:60]}..."


@entrypoint()
async def chat_entrypoint(message: str) -> dict:
    """Chat entrypoint: call the LLM and return the response."""
    response = await chat(message)
    return {"response": response, "summary": summarize_for_log(response)}


all_tasks = [chat]

activity_options = {
    "chat": {
        "execute_in": "activity",
        "start_to_close_timeout": timedelta(seconds=30),
    },
}


@workflow.defn
class ChatFunctionalWorkflow:
    @workflow.run
    async def run(self, message: str) -> dict:
        return await temporal_entrypoint("chat").ainvoke(message)
