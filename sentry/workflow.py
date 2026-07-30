import typing
from dataclasses import dataclass
from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

from sentry.activity import WorkingActivityInput, working_activity

with workflow.unsafe.imports_passed_through():
    from sentry.activity import BrokenActivityInput, broken_activity


@dataclass
class SentryExampleWorkflowInput:
    option: typing.Literal["working", "broken"]


@workflow.defn
class SentryExampleWorkflow:
    @workflow.run
    async def run(self, input: SentryExampleWorkflowInput) -> str:
        workflow.logger.info("Running workflow with parameter %r" % input)

        if input.option == "working":
            return await workflow.execute_activity(
                working_activity,
                WorkingActivityInput(message="Hello, Temporal!"),
                start_to_close_timeout=timedelta(seconds=10),
                retry_policy=RetryPolicy(maximum_attempts=1),
            )

        return await workflow.execute_activity(
            broken_activity,
            BrokenActivityInput(message="Hello, Temporal!"),
            start_to_close_timeout=timedelta(seconds=10),
            retry_policy=RetryPolicy(maximum_attempts=1),
        )
