import uuid
from concurrent.futures import ThreadPoolExecutor

from temporalio.client import Client
from temporalio.contrib.openai_agents.testing import AgentEnvironment, ResponseBuilders, TestModel
from temporalio.worker import Worker

from openai_agents.basic.workflows.dynamic_system_prompt_workflow import (
    DynamicSystemPromptWorkflow,
)


def dynamic_system_prompt_test_model():
    return TestModel.returning_responses(
        [ResponseBuilders.output_message("Style: haiku\nResponse: The weather is cloudy with a chance of meatballs.")]
    )


async def test_execute_workflow_with_random_style(client: Client):
    task_queue_name = str(uuid.uuid4())

    async with AgentEnvironment(model=dynamic_system_prompt_test_model()) as agent_env:
        client = agent_env.applied_on_client(client)
        async with Worker(
            client,
            task_queue=task_queue_name,
            workflows=[DynamicSystemPromptWorkflow],
            activity_executor=ThreadPoolExecutor(5),
        ):
            result = await client.execute_workflow(
                DynamicSystemPromptWorkflow.run,
                "Tell me about the weather today.",
                id=str(uuid.uuid4()),
                task_queue=task_queue_name,
            )

            # Verify the result has the expected format
            assert "Style:" in result
            assert "Response:" in result
            assert any(style in result for style in ["haiku", "pirate", "robot"])


async def test_execute_workflow_with_specific_style(client: Client):
    task_queue_name = str(uuid.uuid4())

    async with AgentEnvironment(model=dynamic_system_prompt_test_model()) as agent_env:
        client = agent_env.applied_on_client(client)
        async with Worker(
            client,
            task_queue=task_queue_name,
            workflows=[DynamicSystemPromptWorkflow],
            activity_executor=ThreadPoolExecutor(5),
        ):
            result = await client.execute_workflow(
                DynamicSystemPromptWorkflow.run,
                args=["Tell me about the weather today.", "haiku"],
                id=str(uuid.uuid4()),
                task_queue=task_queue_name,
            )

            # Verify the result has the expected format and style
            assert "Style: haiku" in result
            assert "Response:" in result
