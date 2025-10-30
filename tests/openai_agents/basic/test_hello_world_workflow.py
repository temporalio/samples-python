import uuid
from concurrent.futures import ThreadPoolExecutor

from temporalio.client import Client
from temporalio.contrib.openai_agents.testing import (
    AgentEnvironment,
    ResponseBuilders,
    TestModel,
)
from temporalio.worker import Worker

from openai_agents.basic.workflows.hello_world_workflow import HelloWorldAgent


def hello_world_test_model():
    return TestModel.returning_responses(
        [ResponseBuilders.output_message("This is a haiku (not really)")]
    )


async def test_execute_workflow(client: Client):
    task_queue_name = str(uuid.uuid4())

    async with AgentEnvironment(model=hello_world_test_model()) as agent_env:
        client = agent_env.applied_on_client(client)
        async with Worker(
            client,
            task_queue=task_queue_name,
            workflows=[HelloWorldAgent],
            activity_executor=ThreadPoolExecutor(5),
        ):
            result = await client.execute_workflow(
                HelloWorldAgent.run,
                "Write a recursive haiku about recursive haikus.",
                id=str(uuid.uuid4()),
                task_queue=task_queue_name,
            )
            assert result == "This is a haiku (not really)"
