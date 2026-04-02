"""Approval Workflow Definition (Signal-based).

This workflow demonstrates human-in-the-loop approval using:
- run_in_workflow=True to access Temporal operations from graph nodes
- Temporal signals for receiving human input
- Temporal queries for checking pending approvals
"""

from dataclasses import dataclass
from typing import Any, cast

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from temporalio.contrib.langgraph import compile as lg_compile

    from langgraph_plugin.graph_api.human_in_the_loop.approval_wait_condition.graph import (
        ApprovalState,
    )


@dataclass
class ApprovalRequest:
    """Input for the approval workflow."""

    request_type: str
    amount: float
    request_data: dict[str, Any] | None = None


@dataclass
class GraphStateResponse:
    """Response from get_graph_state query."""

    values: ApprovalState
    """Current state values from the graph."""

    next: list[str]
    """Next node(s) to execute."""

    step: int
    """Current execution step count."""

    interrupted: bool
    """Whether the graph is currently interrupted."""

    interrupt_node: str | None
    """Node that triggered the interrupt, if any."""

    interrupt_value: dict[str, Any] | None
    """Value passed to interrupt(), if any."""


@workflow.defn
class ApprovalWorkflow:
    """Workflow that pauses for human approval before executing actions.

    This demonstrates using run_in_workflow=True to access Temporal
    operations directly from graph nodes:
    1. Graph runs until request_approval node
    2. request_approval node (run_in_workflow=True) waits for signal
    3. Signal received, approval response stored
    4. Graph continues with execute_action node
    """

    def __init__(self) -> None:
        self._approval_response: dict[str, Any] | None = None
        self._pending_approval: dict[str, Any] | None = None
        self._app: Any = None  # Store runner for visualization queries

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
            The pending approval request details, or None.
        """
        return self._pending_approval

    @workflow.query
    def get_status(self) -> str:
        """Query to get the current workflow status."""
        if self._pending_approval is None:
            return "processing"
        elif self._approval_response is None:
            return "waiting_for_approval"
        else:
            return "approved" if self._approval_response.get("approved") else "rejected"

    @workflow.query
    def get_graph_ascii(self) -> str:
        """Query to get ASCII art visualization of graph execution progress.

        Returns an ASCII diagram showing which nodes have completed,
        which is currently executing/interrupted, and which are pending.
        """
        if self._app is None:
            return "Graph not yet initialized"
        return self._app.get_graph_ascii()

    @workflow.query
    def get_graph_mermaid(self) -> str:
        """Query to get Mermaid diagram of graph execution progress.

        Returns a Mermaid flowchart with nodes colored by status:
        - Green: completed nodes
        - Yellow: current/interrupted node
        - Gray: pending nodes

        Can be rendered in GitHub, Notion, or any Mermaid-compatible viewer.
        """
        if self._app is None:
            return "Graph not yet initialized"
        return self._app.get_graph_mermaid()

    @workflow.query
    def get_graph_state(self) -> GraphStateResponse:
        """Query to get the current graph execution state.

        Returns a GraphStateResponse with typed ApprovalState values.
        """
        if self._app is None:
            return GraphStateResponse(
                values=cast(ApprovalState, {}),
                next=[],
                step=0,
                interrupted=False,
                interrupt_node=None,
                interrupt_value=None,
            )
        snapshot = self._app.get_state()
        interrupt_task = snapshot.tasks[0] if snapshot.tasks else None
        return GraphStateResponse(
            values=cast(ApprovalState, snapshot.values),
            next=list(snapshot.next),
            step=snapshot.metadata.get("step", 0) if snapshot.metadata else 0,
            interrupted=bool(snapshot.tasks),
            interrupt_node=interrupt_task.get("interrupt_node")
            if interrupt_task
            else None,
            interrupt_value=interrupt_task.get("interrupt_value")
            if interrupt_task
            else None,
        )

    @workflow.run
    async def run(self, request: ApprovalRequest) -> dict[str, Any]:
        """Run the approval workflow.

        Args:
            request: The approval request details.

        Returns:
            The final state containing result and executed status.
        """
        self._app = lg_compile("approval_workflow")

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

        # Run the graph - the request_approval node will wait for signal internally
        result = await self._app.ainvoke(initial_state)

        return result
