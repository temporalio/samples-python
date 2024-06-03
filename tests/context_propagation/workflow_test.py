import uuid

from temporalio import activity
from temporalio.client import Client
from temporalio.exceptions import ApplicationError
from temporalio.worker import Worker

from context_propagation.interceptor import ContextPropagationInterceptor
from context_propagation.shared import user_id
from context_propagation.workflows import SayHelloWorkflow


async def test_workflow_with_context_propagator(client: Client):
    # Mock out the activity to assert the context value
    @activity.defn(name="say_hello_activity")
    async def say_hello_activity_mock(name: str) -> str:
        try:
            assert user_id.get() == "test-user"
        except Exception as err:
            raise ApplicationError("Assertion fail", non_retryable=True) from err
        return f"Mock for {name}"

    # Replace interceptors in client
    new_config = client.config()
    new_config["interceptors"] = [ContextPropagationInterceptor()]
    client = Client(**new_config)
    task_queue = f"tq-{uuid.uuid4()}"

    async with Worker(
        client,
        task_queue=task_queue,
        activities=[say_hello_activity_mock],
        workflows=[SayHelloWorkflow],
    ):
        # Set the user during start/signal, but unset after
        token = user_id.set("test-user")
        handle = await client.start_workflow(
            SayHelloWorkflow.run,
            "some-name",
            id=f"wf-{uuid.uuid4()}",
            task_queue=task_queue,
        )
        await handle.signal(SayHelloWorkflow.signal_complete)
        user_id.reset(token)
        result = await handle.result()
    assert result == "Mock for some-name"
