import uuid
from concurrent.futures import ThreadPoolExecutor

from temporalio.client import Client
from temporalio.contrib.openai_agents.testing import AgentEnvironment, ResponseBuilders, TestModel
from temporalio.worker import Worker

from openai_agents.basic.workflows.agent_lifecycle_workflow import (
    AgentLifecycleWorkflow,
)


def agent_lifecycle_test_model():
    return TestModel.returning_responses(
        [ResponseBuilders.output_message('{"number": 10}')]
    )


async def test_execute_workflow(client: Client):
    task_queue_name = str(uuid.uuid4())

    async with AgentEnvironment(model=agent_lifecycle_test_model()) as agent_env:
        client = agent_env.applied_on_client(client)
        async with Worker(
            client,
            task_queue=task_queue_name,
            workflows=[AgentLifecycleWorkflow],
            activity_executor=ThreadPoolExecutor(5),
        ):
            result = await client.execute_workflow(
                AgentLifecycleWorkflow.run,
                10,  # max_number parameter
                id=str(uuid.uuid4()),
                task_queue=task_queue_name,
            )

            # Verify the result has the expected structure
            assert isinstance(result.number, int)
            assert (
                0 <= result.number <= 20
            )  # Should be between 0 and max*2 due to multiply operation
