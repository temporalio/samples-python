import asyncio

from temporalio.client import Client

import hello_nexus.basic.caller.app
import hello_nexus.basic.caller.workflows
import hello_nexus.basic.handler.worker
import hello_nexus.without_service_definition.app
from tests.hello_nexus.helpers import create_nexus_endpoint, delete_nexus_endpoint


async def test_nexus_service_basic(client: Client):
    create_response = await create_nexus_endpoint(
        name=hello_nexus.basic.caller.workflows.NEXUS_ENDPOINT,
        task_queue=hello_nexus.basic.handler.worker.TASK_QUEUE,
        client=client,
    )
    try:
        handler_worker_task = asyncio.create_task(
            hello_nexus.basic.handler.worker.main(
                client,
            )
        )
        await asyncio.sleep(1)
        results = await hello_nexus.basic.caller.app.execute_caller_workflow(
            client,
        )
        hello_nexus.basic.handler.worker.interrupt_event.set()
        await handler_worker_task
        hello_nexus.basic.handler.worker.interrupt_event.clear()
        print("\n\n")
        print([r.message for r in results])
        print("\n\n")
        assert [r.message for r in results] == [
            "Hello world from sync operation!",
            "Hello world from workflow run operation!",
        ]
    finally:
        await delete_nexus_endpoint(
            id=create_response.endpoint.id,
            version=create_response.endpoint.version,
            client=client,
        )
