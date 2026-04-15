"""Human-in-the-loop chatbot using the LangGraph Graph API with Temporal.

Demonstrates using LangGraph's interrupt() to pause a workflow for human input,
combined with Temporal signals to receive the input asynchronously.
"""

from datetime import timedelta

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import START, StateGraph
from langgraph.types import Command, interrupt
from temporalio import workflow
from temporalio.contrib.langgraph import graph


async def generate_draft(message: str) -> str:
    """Generate a draft response. Replace with an LLM call in production."""
    return (
        f"Here's my response to '{message}': "
        "The answer is 42. Let me know if this helps!"
    )


async def human_review(draft: str) -> str:
    """Present draft to human for review via interrupt."""
    feedback = interrupt(draft)
    if feedback == "approve":
        return draft
    return f"[Revised] {draft} (incorporating feedback: {feedback})"


def build_graph() -> StateGraph:
    """Construct the chatbot graph: generate_draft -> human_review."""
    timeout = {"start_to_close_timeout": timedelta(seconds=30)}
    g = StateGraph(str)
    g.add_node("generate_draft", generate_draft, metadata=timeout)
    g.add_node("human_review", human_review, metadata=timeout)
    g.add_edge(START, "generate_draft")
    g.add_edge("generate_draft", "human_review")
    return g


@workflow.defn
class ChatbotWorkflow:
    def __init__(self) -> None:
        self._human_input: str | None = None
        self._draft: str | None = None

    @workflow.signal
    async def provide_feedback(self, feedback: str) -> None:
        """Signal handler: receives human feedback (approval or revision)."""
        self._human_input = feedback

    @workflow.query
    def get_draft(self) -> str | None:
        """Query handler: returns the pending draft for review, or None."""
        return self._draft

    @workflow.run
    async def run(self, user_message: str) -> str:
        g = graph("chatbot").compile(checkpointer=InMemorySaver())
        config = RunnableConfig(
            {"configurable": {"thread_id": workflow.info().workflow_id}}
        )

        # First invocation: runs generate_draft, then pauses at interrupt()
        result = await g.ainvoke(user_message, config, version="v2")

        # Store the draft from the interrupt for the query handler
        self._draft = result.interrupts[0].value

        # Wait for human feedback via Temporal signal
        await workflow.wait_condition(lambda: self._human_input is not None)

        # Resume the graph with the human's feedback
        resumed = await g.ainvoke(
            Command(resume=self._human_input), config, version="v2"
        )
        return resumed.value
