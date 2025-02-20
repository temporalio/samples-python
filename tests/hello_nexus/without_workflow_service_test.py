from temporalio.client import Client

from hello_nexus.without_service_definition.app import (
    NEXUS_ENDPOINT,
    TASK_QUEUE,
    execute_caller_workflow,
)
from tests.hello_nexus.helpers import create_nexus_endpoint, delete_nexus_endpoint


# TODO(dan): This test is very slow (~10s) compared to tests/hello_nexus/basic_test.py.
# One difference is that in this test there is only one worker, polling for both workflow
# and nexus tasks.
async def test_nexus_service_without_service_definition(client: Client):
    create_response = await create_nexus_endpoint(
        name=NEXUS_ENDPOINT,
        task_queue=TASK_QUEUE,
        client=client,
    )
    try:
        result = await execute_caller_workflow(client)
        assert result == "Hello world from sync operation!"
    finally:
        await delete_nexus_endpoint(
            id=create_response.endpoint.id,
            version=create_response.endpoint.version,
            client=client,
        )
