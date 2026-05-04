"""Human-in-the-loop chatbot using the LangGraph Functional API with Temporal.

The @entrypoint pauses at interrupt(); the Workflow waits indefinitely with
workflow.wait_condition() until a Temporal signal delivers human feedback,
then resumes the entrypoint with Command(resume=...).
"""

from datetime import timedelta
from typing import Any

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.func import entrypoint, task
from langgraph.types import Command, interrupt
from temporalio import workflow
from temporalio.contrib.langgraph import entrypoint as temporal_entrypoint


@task
def generate_draft(message: str) -> str:
    """Generate a draft response. Replace with an LLM call in production."""
    return (
        f"Here's my response to '{message}': "
        "The answer is 42. Let me know if this helps!"
    )


@task
def request_human_review(draft: str) -> str:
    """Pause execution to request human review of the draft."""
    feedback = interrupt(draft)
    if feedback == "approve":
        return draft
    return f"[Revised] {draft} (incorporating feedback: {feedback})"


@entrypoint()
async def chatbot_entrypoint(user_message: str) -> dict:
    """Chatbot entrypoint: generate a draft, get human review, return result."""
    draft = await generate_draft(user_message)
    final_response = await request_human_review(draft)
    return {"response": final_response}


all_tasks = [generate_draft, request_human_review]

activity_options = {
    "generate_draft": {
        "execute_in": "activity",
        "start_to_close_timeout": timedelta(seconds=30),
    },
    "request_human_review": {
        "execute_in": "activity",
        "start_to_close_timeout": timedelta(seconds=30),
    },
}


@workflow.defn
class ChatbotFunctionalWorkflow:
    def __init__(self) -> None:
        self._human_input: str | None = None
        self._draft: str | None = None

    @workflow.signal
    async def provide_feedback(self, feedback: str) -> None:
        """Signal handler: receives human feedback."""
        self._human_input = feedback

    @workflow.query
    def get_draft(self) -> str | None:
        """Query handler: returns the pending draft for review, or None."""
        return self._draft

    @workflow.run
    async def run(self, user_message: str) -> dict[str, Any]:
        app = temporal_entrypoint("chatbot")
        app.checkpointer = InMemorySaver()
        config = RunnableConfig(
            {"configurable": {"thread_id": workflow.info().workflow_id}}
        )

        # First invocation: runs until interrupt() pauses for human review
        result = await app.ainvoke(user_message, config, version="v2")

        self._draft = result.interrupts[0].value

        # Wait for human feedback via Temporal signal
        await workflow.wait_condition(lambda: self._human_input is not None)

        # Resume with the human's feedback
        resumed = await app.ainvoke(
            Command(resume=self._human_input), config, version="v2"
        )
        return resumed.value
