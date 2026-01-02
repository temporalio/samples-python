"""Temporal Workflow Definitions for Functional API.

The @entrypoint function runs directly in the Temporal workflow sandbox.
This is possible because:
1. LangGraph modules are passed through the sandbox
2. @task calls are routed to activities via CONFIG_KEY_CALL injection
3. LangGraph's internal machinery (Pregel, call(), etc.) is deterministic

The sandbox enforces determinism - if users use time.time(), random(), etc.
in entrypoint code, Temporal will reject it. Non-deterministic operations
belong in @task functions (which become activities).
"""

from typing import Any

from temporalio import workflow
from temporalio.contrib.langgraph import compile


@workflow.defn
class DocumentWorkflow:
    """Workflow that generates a document using the functional API.

    The @entrypoint function (document_workflow) runs in the workflow sandbox.
    Each @task call within it becomes a Temporal activity execution.
    """

    @workflow.run
    async def run(self, topic: str) -> dict[str, Any]:
        """Generate a document about the given topic.

        Args:
            topic: The topic to write about.

        Returns:
            The generated document with metadata.
        """
        # Get the runner by name - the @entrypoint Pregel is registered
        app = compile("document_workflow")

        # Execute - runs entrypoint in workflow, @task calls become activities
        result = await app.ainvoke(topic)

        return result


@workflow.defn
class ReviewWorkflow:
    """Workflow with human-in-the-loop review.

    Demonstrates:
    - Entrypoint runs in workflow sandbox
    - interrupt() pauses workflow and waits for signal
    - Full control over Temporal features (signals, queries, etc.)
    """

    def __init__(self) -> None:
        self._resume_value: dict[str, Any] | None = None
        self._waiting_for_review: bool = False
        self._interrupt_value: dict[str, Any] | None = None

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
            "interrupt_value": self._interrupt_value,
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

        # Execute - entrypoint runs in workflow
        # When interrupt() is called, the plugin pauses and returns interrupt info
        # We then wait for the resume signal
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
        self._interrupt_value = interrupt_value

        # Wait for resume signal
        await workflow.wait_condition(lambda: self._resume_value is not None)

        self._waiting_for_review = False
        return self._resume_value  # type: ignore[return-value]
