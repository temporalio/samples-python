"""Temporal Workflow Definitions for Functional API.

These workflows use the in-workflow API to execute LangGraph functional
entrypoints. Since @entrypoint returns a Pregel (same as StateGraph.compile()),
we can use compile() just like the Graph API.

Each @task call becomes a Temporal activity.
"""

from typing import Any

from temporalio import workflow
from temporalio.contrib.langgraph import compile


@workflow.defn
class DocumentWorkflow:
    """Workflow that generates a document using the functional API.

    Demonstrates:
    - Using compile() to get the entrypoint runner by name
    - Executing with ainvoke()
    - Each @task call runs as a Temporal activity
    """

    @workflow.run
    async def run(self, topic: str) -> dict[str, Any]:
        """Generate a document about the given topic.

        Args:
            topic: The topic to write about.

        Returns:
            The generated document with metadata.
        """
        # Get the runner by name - @entrypoint returns a Pregel just like graphs
        app = compile("document_workflow")

        # Execute - each @task call becomes a Temporal activity
        result = await app.ainvoke(topic)

        return result


@workflow.defn
class ReviewWorkflow:
    """Workflow with human-in-the-loop review.

    Demonstrates:
    - interrupt() pauses and waits for signal
    - Workflow handles signal and continues execution
    - Full control over Temporal features (signals, queries, etc.)
    """

    def __init__(self) -> None:
        self._resume_value: dict[str, Any] | None = None
        self._waiting_for_review: bool = False
        self._draft: dict[str, Any] | None = None

    @workflow.signal
    async def resume(self, value: dict[str, Any]) -> None:
        """Signal to resume after interrupt.

        Args:
            value: The review decision (e.g., {"decision": "approve"})
        """
        self._resume_value = value

    @workflow.query
    def get_status(self) -> dict[str, Any]:
        """Query current workflow status."""
        return {
            "waiting_for_review": self._waiting_for_review,
            "draft": self._draft,
        }

    @workflow.run
    async def run(self, topic: str) -> dict[str, Any]:
        """Generate and review a document.

        Args:
            topic: The topic to write about.

        Returns:
            The final result after review.
        """
        app = compile("review_workflow")

        # Execute - will pause at interrupt() and return interrupt info
        # NOTE: on_interrupt is a proposed API extension for functional entrypoints
        result = await app.ainvoke(
            topic,
            # Callback for interrupt handling (proposed API)
            on_interrupt=self._handle_interrupt,  # type: ignore[call-arg]
        )

        return result

    async def _handle_interrupt(self, interrupt_value: dict[str, Any]) -> dict[str, Any]:
        """Handle interrupt() by waiting for resume signal.

        Args:
            interrupt_value: The value passed to interrupt() in the entrypoint.

        Returns:
            The value to resume with (from signal).
        """
        self._waiting_for_review = True
        self._draft = interrupt_value.get("document")

        # Wait for resume signal
        await workflow.wait_condition(lambda: self._resume_value is not None)

        self._waiting_for_review = False
        return self._resume_value  # type: ignore[return-value]
