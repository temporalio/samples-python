import uuid

from temporalio import activity
from temporalio.client import Client
from temporalio.contrib.langsmith import LangSmithPlugin
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from langsmith_tracing.basic.activities import OpenAIRequest
from langsmith_tracing.basic.workflows import BasicLLMWorkflow


async def test_basic_workflow(client: Client, env: WorkflowEnvironment):
    expected_text = "Temporal is a durable execution platform."

    @activity.defn(name="call_openai")
    async def mock_call_openai(request: OpenAIRequest) -> str:
        return expected_text

    async with Worker(
        client,
        task_queue="test-langsmith-basic",
        workflows=[BasicLLMWorkflow],
        activities=[mock_call_openai],
        plugins=[LangSmithPlugin()],
    ):
        result = await client.execute_workflow(
            BasicLLMWorkflow.run,
            "What is Temporal?",
            id=f"test-basic-{uuid.uuid4().hex[:8]}",
            task_queue="test-langsmith-basic",
        )

    assert result == expected_text
