import uuid
from datetime import timedelta

from temporalio import activity
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from sleep_for_days.starter import TASK_QUEUE
from sleep_for_days.workflows import SendEmailInput, SleepForDaysWorkflow


async def test_sleep_for_days_workflow():
    num_activity_executions = 0

    # Mock out the activity to count executions
    @activity.defn(name="send_email")
    async def send_email_mock(input: SendEmailInput) -> str:
        nonlocal num_activity_executions
        num_activity_executions += 1
        return input.email_msg

    async with await WorkflowEnvironment.start_time_skipping() as env:
        # if env.supports_time_skipping:
        #     pytest.skip(
        #         "Java test server: https://github.com/temporalio/sdk-java/issues/1903"
        #     )
        async with Worker(
            env.client,
            task_queue=TASK_QUEUE,
            workflows=[SleepForDaysWorkflow],
            activities=[send_email_mock],
        ):
            handle = await env.client.start_workflow(
                SleepForDaysWorkflow.run,
                id=str(uuid.uuid4()),
                task_queue=TASK_QUEUE,
            )

            start_time = await env.get_current_time()
            # Time-skip 5 minutes.
            await env.sleep(timedelta(minutes=5))
            # Check that the activity has been called, we're now waiting for the sleep to finish.
            assert num_activity_executions == 1
            # Time-skip 3 days.
            await env.sleep(timedelta(days=90))
            # Expect 3 more activity calls.
            assert num_activity_executions == 4
            # Send the signal to complete the workflow.
            await handle.signal(SleepForDaysWorkflow.complete)
            # Expect no more activity calls to have been made - workflow is complete.
            assert num_activity_executions == 4
            # Expect more than 90 days to have passed.
            assert (await env.get_current_time() - start_time) > timedelta(days=90)
