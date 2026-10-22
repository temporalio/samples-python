from dataclasses import dataclass
from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy


@dataclass
class ConversationInput:
    affinity_enabled: bool
    steps: int


@workflow.defn
class ProcessConversation:
    @workflow.run
    async def run(self, input: ConversationInput) -> None:
        session_options = (
            workflow.ActivitySessionOptions.workflow_session()
            if input.affinity_enabled
            else None
        )
        for step in range(input.steps):
            await workflow.execute_activity(
                "conversation_step",
                step,
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=RetryPolicy(maximum_attempts=1),
                session_options=session_options,
            )
