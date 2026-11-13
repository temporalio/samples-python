"""Approval before a tool runs, with the wait as a Workflow Update.

``delete_file`` carries ``approval_mode="always_require"``, Agent Framework's
own approval setting. The run returns with the request in
``response.user_input_requests`` instead of calling the tool. The Workflow
publishes the request through a Query, waits for a ``decide`` Update, and sends
the decision back on the same session. Only an approved call runs the tool.
"""

# @@@SNIPSTART python-agent-framework-human-in-the-loop-workflow
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any

from agent_framework import Agent, Content, tool
from temporalio import workflow
from temporalio.agent_framework import TemporalChatClient


@tool(approval_mode="always_require")
def delete_file(path: str) -> str:
    """Delete a file. Runs only after a person approves."""
    return f"deleted {path}"


@dataclass
class ApprovalRequest:
    request_id: str
    tool_name: str
    arguments: dict[str, Any] = field(default_factory=dict)


def approval_request(request: Content) -> ApprovalRequest:
    call = request.function_call
    return ApprovalRequest(
        request_id=request.id or "",
        tool_name=(call.name if call is not None else None) or "",
        arguments=(call.parse_arguments() if call is not None else None) or {},
    )


@workflow.defn
class HumanInTheLoopWorkflow:
    def __init__(self) -> None:
        self._pending: list[ApprovalRequest] = []
        self._decision: str | None = None

    @workflow.query
    def pending_approvals(self) -> list[ApprovalRequest]:
        return list(self._pending)

    @workflow.update
    async def decide(self, decision: str) -> str:
        # Applies to every pending request. The validator below runs before the
        # Workflow sees the model's reply, so it checks the input, not the state.
        self._decision = decision
        return decision

    @decide.validator
    def validate_decide(self, decision: str) -> None:
        # Anything else never enters the Workflow's history.
        if decision not in ("approve", "reject"):
            raise ValueError(
                f"decision must be 'approve' or 'reject', not {decision!r}"
            )

    @workflow.run
    async def run(self, prompt: str) -> str:
        agent = Agent(
            client=TemporalChatClient(
                "gpt-4o-mini", start_to_close_timeout=timedelta(seconds=60)
            ),
            instructions="You manage files. Use delete_file when asked to delete one.",
            tools=[delete_file],
        )
        # Approvals are keyed by the function call's id and resolved against
        # the session, so both runs use the same session.
        session = agent.create_session()
        response = await agent.run(prompt, session=session)
        while response.user_input_requests:
            requests = response.user_input_requests
            self._pending = [approval_request(request) for request in requests]
            await workflow.wait_condition(lambda: self._decision is not None)
            approved = self._decision == "approve"
            self._decision = None
            self._pending = []
            response = await agent.run(
                [
                    request.to_function_approval_response(approved)
                    for request in requests
                ],
                session=session,
            )
        return response.text


# @@@SNIPEND
