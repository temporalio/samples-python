import uuid
from datetime import timedelta

import pytest
from temporalio import nexus
from temporalio.service import RPCError
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from nexus_completion_callbacks.caller.completion_handler import (
    CallbackContext,
    GreetingCompletionHandler,
)
from nexus_completion_callbacks.caller.workflows import (
    RecordCompletionInput,
    RecordCompletionWorkflow,
)
from nexus_completion_callbacks.handler.service_handler import (
    GreetingServiceHandler,
    create_greeting,
)
from nexus_completion_callbacks.service import (
    GreetingInput,
    GreetingService,
)
from tests.helpers import assert_eventually
from tests.helpers.nexus import create_nexus_endpoint, delete_nexus_endpoint

DEV_SERVER_DOWNLOAD_VERSION = "v1.9.2-nexus-handler-callbacks"


async def test_completion_callback_receives_operation_result(
    env: WorkflowEnvironment,
) -> None:
    if env.supports_time_skipping:
        pytest.skip("Time-skipping server does not support standalone Nexus operations")
    async with await WorkflowEnvironment.start_local(
        dev_server_download_version=DEV_SERVER_DOWNLOAD_VERSION,
        dev_server_extra_args=[
            "--dynamic-config-value",
            "activity.enableCallbacks=true",
        ],
    ) as callbacks_env:
        await _run_sample(callbacks_env)


async def _run_sample(env: WorkflowEnvironment) -> None:
    client = env.client
    endpoint_name = f"test-nexus-completion-callbacks-{uuid.uuid4()}"
    task_queue = f"nexus-completion-callbacks-{uuid.uuid4()}"
    completion_task_queue = f"nexus-completion-callbacks-completion-{uuid.uuid4()}"
    create_response = await create_nexus_endpoint(
        name=endpoint_name,
        task_queue=task_queue,
        client=client,
    )
    try:
        async with (
            Worker(
                client,
                task_queue=task_queue,
                activities=[create_greeting],
                nexus_service_handlers=[GreetingServiceHandler()],
            ),
            Worker(
                client,
                task_queue=completion_task_queue,
                nexus_service_handlers=[GreetingCompletionHandler()],
                workflows=[RecordCompletionWorkflow],
            ),
        ):
            operation_id = str(uuid.uuid4())
            _ = await client.create_nexus_client(
                service=GreetingService,
                endpoint=endpoint_name,
            ).start_operation(
                GreetingService.greet,
                GreetingInput(name="Test"),
                id=operation_id,
                schedule_to_close_timeout=timedelta(seconds=10),
                completion_callbacks=[
                    nexus.create_completion_callback(
                        operation=GreetingCompletionHandler.on_complete,
                        task_queue=completion_task_queue,
                        source_context=CallbackContext(operation_id=operation_id),
                    )
                ],
            )

            handle = client.get_workflow_handle(f"on-complete-{operation_id}")

            # The callback starts the record workflow, so wait for it to complete.
            async def record_completed() -> None:
                try:
                    await handle.result()
                except RPCError as err:
                    raise AssertionError("record workflow not started yet") from err

            await assert_eventually(record_completed)

            # The start event holds the delivered outcome and links to the operation.
            started = (await handle.fetch_history()).events[0]
            [record] = await client.data_converter.decode(
                started.workflow_execution_started_event_attributes.input.payloads,
                [RecordCompletionInput],
            )
            assert record == RecordCompletionInput(operation_id, message="Hello, Test!")
            assert operation_id in [
                link.callback.execution.business_id for link in started.links
            ]
    finally:
        _ = await delete_nexus_endpoint(
            id=create_response.endpoint.id,
            version=create_response.endpoint.version,
            client=client,
        )
