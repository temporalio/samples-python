"""Human-in-the-Loop Workflow.

Temporal workflow that demonstrates interrupt() handling with signals and queries.
"""

from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from langgraph.types import Command
    from temporalio.contrib.langgraph import activity_options, compile_functional


@dataclass
class ApprovalRequest:
    """Input for the approval workflow."""

    request_type: str
    amount: float
    request_data: dict[str, Any] | None = None


@workflow.defn
class ApprovalWorkflow:
    """Workflow that pauses for human approval before executing actions.

    This demonstrates the full interrupt flow with the functional API:
    1. Entrypoint runs until interrupt() is called
    2. Workflow receives __interrupt__ in result with approval request details
    3. Workflow waits for signal with human input (with optional timeout)
    4. Workflow resumes entrypoint with Command(resume=response)
    5. Entrypoint completes execution
    """

    def __init__(self) -> None:
        self._approval_response: dict[str, Any] | None = None
        self._interrupt_value: dict[str, Any] | None = None

    @workflow.signal
    def provide_approval(self, response: dict[str, Any]) -> None:
        """Signal to provide approval response.

        Args:
            response: Dict with 'approved' (bool), 'reason' (str), 'approver' (str)
        """
        self._approval_response = response

    @workflow.query
    def get_pending_approval(self) -> dict[str, Any] | None:
        """Query to get the current pending approval request."""
        return self._interrupt_value

    @workflow.query
    def get_status(self) -> str:
        """Query to get the current workflow status."""
        if self._interrupt_value is None:
            return "processing"
        elif self._approval_response is None:
            return "waiting_for_approval"
        else:
            return "approved" if self._approval_response.get("approved") else "rejected"

    @workflow.run
    async def run(
        self,
        request: ApprovalRequest,
        approval_timeout: timedelta | None = None,
    ) -> dict[str, Any]:
        """Run the approval workflow.

        Args:
            request: The approval request details.
            approval_timeout: Optional timeout for waiting for approval.

        Returns:
            The final state containing result and executed status.
        """
        # Workflow-level task options override plugin-level settings.
        # This demonstrates how to customize timeouts per-workflow when needed.
        # The plugin's task_options set defaults; compile_functional can override.
        app = compile_functional(
            "approval_entrypoint",
            task_options={
                "process_request": activity_options(
                    start_to_close_timeout=timedelta(
                        seconds=10
                    ),  # Override plugin default
                ),
                # execute_action uses plugin default (30s) - not specified here
            },
        )

        # Handle both dataclass and dict input
        if isinstance(request, dict):
            request_type = request.get("request_type", "unknown")
            amount = request.get("amount", 0.0)
            request_data = request.get("request_data") or {}
        else:
            request_type = request.request_type
            amount = request.amount
            request_data = request.request_data or {}

        # First invocation - should hit interrupt
        result = await app.ainvoke(
            request_type,
            config={
                "configurable": {
                    "amount": amount,
                    "request_data": request_data,
                }
            },
            on_interrupt=self._handle_interrupt,
        )

        return result

    async def _handle_interrupt(
        self, interrupt_value: dict[str, Any]
    ) -> dict[str, Any]:
        """Handle interrupt() by waiting for approval signal.

        Args:
            interrupt_value: The value passed to interrupt().

        Returns:
            The approval response from the signal.
        """
        self._interrupt_value = interrupt_value

        workflow.logger.info(
            "Workflow paused for approval: %s", interrupt_value.get("message")
        )

        # Wait for approval signal
        await workflow.wait_condition(
            lambda: self._approval_response is not None,
        )

        workflow.logger.info(
            "Received approval response: approved=%s",
            self._approval_response.get("approved")
            if self._approval_response
            else None,
        )

        return self._approval_response  # type: ignore[return-value]
