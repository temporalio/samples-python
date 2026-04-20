import uuid

import pytest
from openai.types.responses import Response
from temporalio import activity
from temporalio.client import Client
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

try:
    from temporalio.contrib.langsmith import LangSmithPlugin
except ImportError:
    LangSmithPlugin = None  # type: ignore[assignment,misc]

from langsmith_tracing.basic.activities import OpenAIRequest
from langsmith_tracing.basic.workflows import BasicLLMWorkflow
from tests.langsmith_tracing.helpers import make_text_response

pytestmark = pytest.mark.skipif(
    LangSmithPlugin is None,
    reason="temporalio.contrib.langsmith not available",
)


async def test_basic_workflow(client: Client, env: WorkflowEnvironment):
    expected_text = "Temporal is a durable execution platform."
    mock_response = make_text_response(expected_text)

    @activity.defn(name="call_openai")
    async def mock_call_openai(request: OpenAIRequest) -> Response:
        return mock_response

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
