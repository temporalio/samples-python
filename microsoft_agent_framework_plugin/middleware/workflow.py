"""Agent Framework middleware running in the Workflow.

Both middleware classes run inside the Workflow, next to the agent's loop, so
they must be deterministic: no clock, no I/O, no randomness. Middleware that
needs I/O calls ``await workflow.execute_activity(...)``.
"""

from collections.abc import Awaitable, Callable, Mapping
from datetime import timedelta

from agent_framework import (
    Agent,
    ChatContext,
    ChatMiddleware,
    FunctionInvocationContext,
    FunctionMiddleware,
    tool,
)
from temporalio import workflow
from temporalio.microsoft_agent_framework import TemporalChatClient


@tool
def delete_file(path: str) -> str:
    """Delete the file at the given path."""
    return f"deleted {path}"


# @@@SNIPSTART python-microsoft-agent-framework-middleware-middleware
ALLOWED_PREFIX = "/tmp/"
REMINDER = "Answer in one short sentence."


class BlockOutsideTmp(FunctionMiddleware):
    """Refuses delete_file calls outside /tmp without running the tool."""

    async def process(
        self,
        context: FunctionInvocationContext,
        call_next: Callable[[], Awaitable[None]],
    ) -> None:
        if context.function.name == "delete_file":
            arguments = context.arguments
            path = str(
                arguments.get("path", "")
                if isinstance(arguments, Mapping)
                else getattr(arguments, "path", "")
            )
            if not path.startswith(ALLOWED_PREFIX):
                # Not calling call_next() skips the tool; the model gets this result.
                context.result = f"Refused: {path} is outside {ALLOWED_PREFIX}"
                return
        await call_next()


class AppendReminder(ChatMiddleware):
    """Adds a reminder to the instructions of every model call."""

    async def process(
        self, context: ChatContext, call_next: Callable[[], Awaitable[None]]
    ) -> None:
        options = dict(context.options or {})
        instructions = options.get("instructions") or ""
        options["instructions"] = f"{instructions} {REMINDER}".strip()
        context.options = options
        await call_next()


# @@@SNIPEND


# @@@SNIPSTART python-microsoft-agent-framework-middleware-workflow
@workflow.defn
class MiddlewareWorkflow:
    @workflow.run
    async def run(self, prompt: str) -> str:
        agent = Agent(
            client=TemporalChatClient(
                "gpt-4o-mini", start_to_close_timeout=timedelta(seconds=60)
            ),
            instructions="You manage files. Use delete_file when asked to delete one.",
            tools=[delete_file],
            middleware=[BlockOutsideTmp(), AppendReminder()],
        )
        response = await agent.run(prompt)
        return response.text


# @@@SNIPEND
