"""Approval Workflow Definition.

This workflow demonstrates human-in-the-loop approval using:
- LangGraph's interrupt() for pausing execution
- Temporal signals for receiving human input
- Temporal queries for checking pending approvals
- Timeout handling for approval deadlines
"""

from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from langgraph.types import Command

    from temporalio.contrib.langgraph import compile as lg_compile


@dataclass
class ApprovalRequest:
    """Input for the approval workflow."""

    request_type: str
    amount: float
    request_data: dict[str, Any] | None = None


@workflow.defn
class ApprovalWorkflow:
    """Workflow that pauses for human approval before executing actions.

    This demonstrates the full interrupt flow:
    1. Graph runs until interrupt() is called in request_approval node
    2. Workflow receives __interrupt__ in result with approval request details
    3. Workflow waits for signal with human input (with optional timeout)
    4. Workflow resumes graph with Command(resume=response)
    5. Graph completes with execute_action node
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
        """Query to get the current pending approval request.

        Returns:
            The interrupt value containing approval request details, or None.
        """
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
                             If None, waits indefinitely.

        Returns:
            The final state containing result and executed status.
        """
        app = lg_compile("approval_workflow")

        # Handle both dataclass and dict input (Temporal deserializes to dict)
        if isinstance(request, dict):
            request_type = request.get("request_type", "unknown")
            amount = request.get("amount", 0.0)
            request_data = request.get("request_data") or {}
        else:
            request_type = request.request_type
            amount = request.amount
            request_data = request.request_data or {}

        # Prepare initial state
        initial_state = {
            "request_type": request_type,
            "amount": amount,
            "request_data": request_data,
        }

        # First invocation - should hit interrupt at request_approval node
        result = await app.ainvoke(initial_state)

        # Check for interrupt
        if "__interrupt__" in result:
            # Store the interrupt value for queries
            self._interrupt_value = result["__interrupt__"][0].value

            workflow.logger.info(
                "Workflow paused for approval: %s", self._interrupt_value.get("message")
            )

            # Wait for approval signal (with optional timeout)
            try:
                await workflow.wait_condition(
                    lambda: self._approval_response is not None,
                    timeout=approval_timeout,
                )
            except TimeoutError:
                # Timeout - auto-reject
                workflow.logger.warning("Approval timeout - auto-rejecting")
                self._approval_response = {
                    "approved": False,
                    "reason": "Approval timeout exceeded",
                    "approver": "system",
                }

            workflow.logger.info(
                "Received approval response: approved=%s",
                self._approval_response.get("approved") if self._approval_response else None,
            )

            # Resume with the approval response
            result = await app.ainvoke(Command(resume=self._approval_response))

        return result
