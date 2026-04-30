from __future__ import annotations

from contextlib import aclosing
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any

from temporalio import workflow
from temporalio.contrib.google_adk_agents import TemporalModel
from temporalio.contrib.google_adk_agents.workflow import activity_tool

with workflow.unsafe.imports_passed_through():
    from google.adk.agents import Agent
    from google.adk.runners import InMemoryRunner
    from google.genai import types

    from google_adk.human_in_the_loop.activities.sensitive_actions import (
        delete_record,
        send_email,
    )


@dataclass
class ApprovalSignal:
    """Signal payload for approving/rejecting a tool call."""

    call_id: str
    approved: bool = True


@dataclass
class PendingToolCall:
    """A tool call awaiting human approval."""

    call_id: str
    tool_name: str
    arguments: dict[str, Any] = field(default_factory=dict)


@workflow.defn
class HumanInTheLoopWorkflow:
    """Agent with human-in-the-loop approval for sensitive tools.

    When the agent attempts to use a tool marked as requiring confirmation,
    the workflow pauses and waits for an approval signal before proceeding.

    - ``approve`` (signal): approve or reject a pending tool call
    - ``get_pending_approvals`` (query): list tool calls awaiting approval
    """

    def __init__(self) -> None:
        self._pending_calls: dict[str, PendingToolCall] = {}
        self._approval_results: dict[str, ApprovalSignal] = {}

    @workflow.run
    async def run(self, prompt: str) -> str:
        # Tools that require human confirmation before execution
        require_confirmation = {"send_email", "delete_record"}

        email_tool = activity_tool(
            send_email, start_to_close_timeout=timedelta(seconds=10)
        )
        delete_tool = activity_tool(
            delete_record, start_to_close_timeout=timedelta(seconds=10)
        )

        wf_self = self

        async def before_tool_callback(
            tool: Any, args: dict[str, Any], tool_context: Any
        ) -> dict[str, Any] | None:
            if tool.name not in require_confirmation:
                return None  # proceed without approval

            # Generate a unique call ID and register as pending
            call_id = str(workflow.uuid4())
            wf_self._pending_calls[call_id] = PendingToolCall(
                call_id=call_id,
                tool_name=tool.name,
                arguments=dict(args),
            )

            # Pause until approval signal arrives
            def _is_approved(cid: str = call_id) -> bool:
                return cid in wf_self._approval_results

            await workflow.wait_condition(_is_approved)

            # Process approval
            approval = wf_self._approval_results.pop(call_id)
            wf_self._pending_calls.pop(call_id, None)

            if not approval.approved:
                return {"error": f"Tool '{tool.name}' was rejected by reviewer."}

            return None  # proceed with execution

        agent = Agent(
            name="AssistantWithApproval",
            model=TemporalModel("gemini-2.5-flash"),
            instruction=(
                "You are a helpful assistant. You can send emails and delete records. "
                "Use these tools when the user asks you to."
            ),
            tools=[email_tool, delete_tool],
            before_tool_callback=before_tool_callback,
        )

        runner = InMemoryRunner(agent=agent, app_name="hitl_agent")
        session = await runner.session_service.create_session(
            user_id="user", app_name="hitl_agent"
        )

        result = ""
        async with aclosing(
            runner.run_async(
                user_id="user",
                session_id=session.id,
                new_message=types.Content(
                    role="user",
                    parts=[types.Part.from_text(text=prompt)],
                ),
            )
        ) as events:
            async for event in events:
                if event.content and event.content.parts:
                    for part in event.content.parts:
                        if part.text:
                            result = part.text

        return result

    @workflow.signal
    async def approve(self, signal: ApprovalSignal) -> None:
        """Approve or reject a pending tool call."""
        self._approval_results[signal.call_id] = signal

    @workflow.query
    def get_pending_approvals(self) -> list[PendingToolCall]:
        """List all tool calls awaiting human approval."""
        return list(self._pending_calls.values())
