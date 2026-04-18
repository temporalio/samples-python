import uuid

import pytest
from openai.types.responses import Response
from openai.types.responses.response_output_message import ResponseOutputMessage
from openai.types.responses.response_output_text import ResponseOutputText
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

# The workflow uses @traceable which requires the LangSmithPlugin's
# aio_to_thread patch to work inside the workflow sandbox.
pytestmark = pytest.mark.skipif(
    LangSmithPlugin is None,
    reason="temporalio.contrib.langsmith not available",
)


def _make_text_response(text: str) -> Response:
    """Build a minimal Response with a text output."""
    return Response.model_construct(
        id="resp_mock",
        created_at=0.0,
        model="gpt-4o-mini",
        object="response",
        output=[
            ResponseOutputMessage.model_construct(
                id="msg_mock",
                type="message",
                role="assistant",
                status="completed",
                content=[
                    ResponseOutputText.model_construct(
                        type="output_text",
                        text=text,
                        annotations=[],
                    )
                ],
            )
        ],
        parallel_tool_calls=False,
        tool_choice="auto",
        tools=[],
    )


async def test_basic_workflow(client: Client, env: WorkflowEnvironment):
    expected_text = "Temporal is a durable execution platform."
    mock_response = _make_text_response(expected_text)

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
