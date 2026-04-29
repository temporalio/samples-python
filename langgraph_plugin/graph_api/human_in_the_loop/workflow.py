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
from typing_extensions import TypedDict


class State(TypedDict):
    value: str


async def generate_draft(state: State) -> dict[str, str]:
    """Generate a draft response. Replace with an LLM call in production."""
    return {
        "value": (
            f"Here's my response to '{state['value']}': "
            "The answer is 42. Let me know if this helps!"
        )
    }


async def human_review(state: State) -> dict[str, str]:
    """Present draft to human for review via interrupt."""
    feedback = interrupt(state["value"])
    if feedback == "approve":
        return {"value": state["value"]}
    return {"value": f"[Revised] {state['value']} (incorporating feedback: {feedback})"}


def make_chatbot_graph() -> StateGraph:
    node_metadata = {
        "execute_in": "activity",
        "start_to_close_timeout": timedelta(seconds=30),
    }
    g = StateGraph(State)
    g.add_node("generate_draft", generate_draft, metadata=node_metadata)
    g.add_node("human_review", human_review, metadata=node_metadata)
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
        app = graph("chatbot").compile(checkpointer=InMemorySaver())
        config = RunnableConfig(
            {"configurable": {"thread_id": workflow.info().workflow_id}}
        )

        # First invocation: runs generate_draft, then pauses at interrupt()
        result = await app.ainvoke({"value": user_message}, config, version="v2")

        # Store the draft from the interrupt for the query handler
        self._draft = result.interrupts[0].value

        # Wait for human feedback via Temporal signal
        await workflow.wait_condition(lambda: self._human_input is not None)

        # Resume the graph with the human's feedback
        resumed = await app.ainvoke(
            Command(resume=self._human_input), config, version="v2"
        )
        return resumed.value["value"]
