"""Approval before a tool runs, with the wait as a Workflow Update.

``delete_file`` carries ``approval_mode="always_require"``, Agent Framework's
own approval setting. The run returns with the request in
``response.user_input_requests`` instead of calling the tool. The Workflow
publishes the request through a Query, waits for a ``decide`` Update for each
request id, and sends the decisions back on the same session. Only an approved
call runs the tool.
"""

# @@@SNIPSTART python-microsoft-agent-framework-human-in-the-loop-workflow
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any

from agent_framework import Agent, AgentResponse, AgentSession, Content, tool
from temporalio import workflow
from temporalio.exceptions import ApplicationError
from temporalio.microsoft_agent_framework import TemporalChatClient


@tool(approval_mode="always_require")
def delete_file(path: str) -> str:
    """Delete a file. Runs only after a person approves."""
    return f"deleted {path}"


@dataclass
class ApprovalRequest:
    request_id: str
    tool_name: str
    arguments: dict[str, Any] = field(default_factory=dict)


@dataclass
class Decision:
    request_id: str
    approved: bool


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
        self._pending: dict[str, ApprovalRequest] = {}
        self._decisions: dict[str, bool] = {}
        self._awaiting_reply = False

    @workflow.query
    def pending_approvals(self) -> list[ApprovalRequest]:
        return list(self._pending.values())

    @workflow.update
    async def decide(self, decision: Decision) -> str:
        # A decision can arrive in the same Workflow Task as the model's reply,
        # before the loop in run has read the requests in that reply. Judge the
        # id once the reply has been read.
        await workflow.wait_condition(lambda: not self._awaiting_reply)
        if decision.request_id in self._decisions:
            raise ApplicationError(
                f"approval request {decision.request_id!r} is already decided",
                non_retryable=True,
            )
        if decision.request_id not in self._pending:
            raise ApplicationError(
                f"no pending approval request {decision.request_id!r}",
                non_retryable=True,
            )
        self._decisions[decision.request_id] = decision.approved
        return "approved" if decision.approved else "rejected"

    @decide.validator
    def validate_decide(self, decision: Decision) -> None:
        # Validators run before the Workflow sees the model's reply, so this one
        # checks the input and not the state. Bad input never enters history.
        if not decision.request_id:
            raise ValueError("request_id is required")

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
        # the session, so every run uses the same session.
        session = agent.create_session()
        response = await self._reply(agent, prompt, session)
        while response.user_input_requests:
            requests = response.user_input_requests
            self._pending = {
                item.request_id: item for item in map(approval_request, requests)
            }
            await workflow.wait_condition(
                lambda: all(
                    request_id in self._decisions for request_id in self._pending
                )
            )
            replies = [
                request.to_function_approval_response(self._decisions[request.id or ""])
                for request in requests
            ]
            self._pending = {}
            response = await self._reply(agent, replies, session)
        return response.text

    async def _reply(
        self, agent: Agent, messages: Any, session: AgentSession
    ) -> AgentResponse:
        self._awaiting_reply = True
        try:
            return await agent.run(messages, session=session)
        finally:
            self._awaiting_reply = False


# @@@SNIPEND
