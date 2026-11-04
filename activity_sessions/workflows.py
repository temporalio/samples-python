import contextlib
from dataclasses import dataclass
from datetime import timedelta

from temporalio import workflow
from temporalio.common import ActivitySessionOptions, UseWorkflowSession


@dataclass
class ConversationInput:
    use_session: bool
    steps: int


@workflow.defn
class ProcessConversation:
    @workflow.run
    async def run(self, input: ConversationInput) -> None:
        # Activities started in the scope run on this workflow's worker.
        session = (
            workflow.activity_session(
                ActivitySessionOptions(placement=UseWorkflowSession())
            )
            if input.use_session
            else contextlib.nullcontext()
        )
        with session:
            for step in range(input.steps):
                await workflow.execute_activity(
                    "conversation_step",
                    step,
                    # Short, so a turn lost with a killed worker is retried soon.
                    start_to_close_timeout=timedelta(seconds=10),
                )
