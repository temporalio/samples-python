import uuid

from temporalio import activity
from temporalio.client import Client
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from litellm_activity.shared import LLMRequest
from litellm_activity.workflow import LiteLLMWorkflow


async def test_litellm_workflow(client: Client, env: WorkflowEnvironment) -> None:
    expected = "Temporal makes LLM calls durable."

    @activity.defn(name="call_litellm")
    async def mock_call_litellm(request: LLMRequest) -> str:
        assert request.prompt == "What does Temporal add to LLM calls?"
        return expected

    task_queue = f"test-litellm-{uuid.uuid4()}"
    async with Worker(
        client,
        task_queue=task_queue,
        workflows=[LiteLLMWorkflow],
        activities=[mock_call_litellm],
    ):
        result = await client.execute_workflow(
            LiteLLMWorkflow.run,
            LLMRequest(prompt="What does Temporal add to LLM calls?"),
            id=f"test-litellm-{uuid.uuid4()}",
            task_queue=task_queue,
        )

    assert result == expected
