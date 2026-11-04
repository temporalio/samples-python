import uuid
from enum import Enum

import pytest
from temporalio import activity, client, exceptions, worker
from temporalio.api.enums.v1 import EventType
from temporalio.testing import WorkflowEnvironment

from message_passing.waiting_for_handlers_and_compensation import (
    WorkflowExitType,
    WorkflowInput,
)
from message_passing.waiting_for_handlers_and_compensation.activities import (
    activity_executed_by_update_handler,
    activity_executed_by_update_handler_to_perform_compensation,
    activity_executed_to_perform_workflow_compensation,
)
from message_passing.waiting_for_handlers_and_compensation.starter import TASK_QUEUE
from message_passing.waiting_for_handlers_and_compensation.workflows import (
    WaitingForHandlersAndCompensationWorkflow,
)


class UpdateExpect(Enum):
    SUCCESS = "success"
    FAILURE = "failure"


class WorkflowExpect(Enum):
    SUCCESS = "success"
    FAILURE = "failure"


@pytest.mark.parametrize(
    ["exit_type_name", "update_expect", "workflow_expect"],
    [
        (WorkflowExitType.SUCCESS.name, UpdateExpect.SUCCESS, WorkflowExpect.SUCCESS),
        (WorkflowExitType.FAILURE.name, UpdateExpect.FAILURE, WorkflowExpect.FAILURE),
        (
            WorkflowExitType.CANCELLATION.name,
            UpdateExpect.FAILURE,
            WorkflowExpect.FAILURE,
        ),
    ],
)
async def test_waiting_for_handlers_and_compensation(
    env: WorkflowEnvironment,
    exit_type_name: str,
    update_expect: UpdateExpect,
    workflow_expect: WorkflowExpect,
):
    [exit_type] = [t for t in WorkflowExitType if t.name == exit_type_name]
    if env.supports_time_skipping:
        pytest.skip(
            "Java test server: https://github.com/temporalio/sdk-java/issues/1903"
        )
    async with worker.Worker(
        env.client,
        task_queue=TASK_QUEUE,
        workflows=[WaitingForHandlersAndCompensationWorkflow],
        activities=[
            activity_executed_by_update_handler,
            activity_executed_by_update_handler_to_perform_compensation,
            activity_executed_to_perform_workflow_compensation,
        ],
    ):
        wf_handle = await env.client.start_workflow(
            WaitingForHandlersAndCompensationWorkflow.run,
            WorkflowInput(exit_type=exit_type),
            id=str(uuid.uuid4()),
            task_queue=TASK_QUEUE,
        )
        up_handle = await wf_handle.start_update(
            WaitingForHandlersAndCompensationWorkflow.my_update,
            wait_for_stage=client.WorkflowUpdateStage.ACCEPTED,
        )

        if exit_type == WorkflowExitType.CANCELLATION:
            await wf_handle.cancel()

        if update_expect == UpdateExpect.SUCCESS:
            await up_handle.result()
            assert not (
                await wf_handle.query(
                    WaitingForHandlersAndCompensationWorkflow.update_compensation_done
                )
            )
        else:
            with pytest.raises(client.WorkflowUpdateFailedError):
                await up_handle.result()
            assert await wf_handle.query(
                WaitingForHandlersAndCompensationWorkflow.update_compensation_done
            )

        if workflow_expect == WorkflowExpect.SUCCESS:
            await wf_handle.result()
            assert not (
                await wf_handle.query(
                    WaitingForHandlersAndCompensationWorkflow.workflow_compensation_done
                )
            )
        else:
            with pytest.raises(client.WorkflowFailureError):
                await wf_handle.result()
            assert await wf_handle.query(
                WaitingForHandlersAndCompensationWorkflow.workflow_compensation_done
            )

        await assert_compensation_state(
            wf_handle,
            workflow_compensated=workflow_expect == WorkflowExpect.FAILURE,
            update_compensated=update_expect == UpdateExpect.FAILURE,
        )


async def test_workflow_compensation_without_update(env: WorkflowEnvironment):
    async with worker.Worker(
        env.client,
        task_queue=TASK_QUEUE,
        workflows=[WaitingForHandlersAndCompensationWorkflow],
        activities=[
            activity_executed_by_update_handler,
            activity_executed_by_update_handler_to_perform_compensation,
            activity_executed_to_perform_workflow_compensation,
        ],
    ):
        wf_handle = await env.client.start_workflow(
            WaitingForHandlersAndCompensationWorkflow.run,
            WorkflowInput(exit_type=WorkflowExitType.CANCELLATION),
            id=str(uuid.uuid4()),
            task_queue=TASK_QUEUE,
        )
        # Ensure the workflow is running before cancelling without an update.
        assert not await wf_handle.query(
            WaitingForHandlersAndCompensationWorkflow.workflow_compensation_done
        )
        await wf_handle.cancel()
        with pytest.raises(client.WorkflowFailureError) as err:
            await wf_handle.result()
        assert isinstance(err.value.cause, exceptions.CancelledError)

        await assert_compensation_state(
            wf_handle, workflow_compensated=True, update_compensated=False
        )


async def test_update_compensation_without_workflow_compensation(
    env: WorkflowEnvironment,
):
    if env.supports_time_skipping:
        pytest.skip(
            "Java test server: https://github.com/temporalio/sdk-java/issues/1903"
        )

    @activity.defn(name="activity_executed_by_update_handler")
    async def failing_update_activity():
        raise exceptions.ApplicationError(
            "deliberately failing update activity", non_retryable=True
        )

    async with worker.Worker(
        env.client,
        task_queue=TASK_QUEUE,
        workflows=[WaitingForHandlersAndCompensationWorkflow],
        activities=[
            failing_update_activity,
            activity_executed_by_update_handler_to_perform_compensation,
            activity_executed_to_perform_workflow_compensation,
        ],
    ):
        wf_handle = await env.client.start_workflow(
            WaitingForHandlersAndCompensationWorkflow.run,
            WorkflowInput(exit_type=WorkflowExitType.SUCCESS),
            id=str(uuid.uuid4()),
            task_queue=TASK_QUEUE,
        )
        with pytest.raises(client.WorkflowUpdateFailedError) as err:
            await wf_handle.execute_update(
                WaitingForHandlersAndCompensationWorkflow.my_update
            )
        assert isinstance(err.value.cause, exceptions.ActivityError)
        assert (await wf_handle.result()).data == "workflow-result"

        await assert_compensation_state(
            wf_handle, workflow_compensated=False, update_compensated=True
        )


async def assert_compensation_state(
    wf_handle: client.WorkflowHandle,
    *,
    workflow_compensated: bool,
    update_compensated: bool,
):
    history = await wf_handle.fetch_history()
    scheduled_activities = {
        event.event_id: event.activity_task_scheduled_event_attributes.activity_type.name
        for event in history.events
        if event.event_type == EventType.EVENT_TYPE_ACTIVITY_TASK_SCHEDULED
    }
    completed_activities = [
        scheduled_activities[
            event.activity_task_completed_event_attributes.scheduled_event_id
        ]
        for event in history.events
        if event.event_type == EventType.EVENT_TYPE_ACTIVITY_TASK_COMPLETED
    ]
    for activity_name, expected in {
        activity_executed_to_perform_workflow_compensation.__name__: workflow_compensated,
        activity_executed_by_update_handler_to_perform_compensation.__name__: update_compensated,
    }.items():
        assert list(scheduled_activities.values()).count(activity_name) == int(expected)
        assert completed_activities.count(activity_name) == int(expected)

    assert (
        await wf_handle.query(
            WaitingForHandlersAndCompensationWorkflow.workflow_compensation_done
        )
        == workflow_compensated
    )
    assert (
        await wf_handle.query(
            WaitingForHandlersAndCompensationWorkflow.update_compensation_done
        )
        == update_compensated
    )
