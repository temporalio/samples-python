import json
import uuid

import pytest
from openai.types.responses import Response
from openai.types.responses.response_function_tool_call import (
    ResponseFunctionToolCall,
)
from temporalio import activity
from temporalio.client import Client
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

try:
    from temporalio.contrib.langsmith import LangSmithPlugin
except ImportError:
    LangSmithPlugin = None  # type: ignore[assignment,misc]

pytestmark = pytest.mark.skipif(
    LangSmithPlugin is None,
    reason="temporalio.contrib.langsmith not available",
)

from langsmith_tracing.chatbot.activities import NoteRequest, OpenAIRequest
from langsmith_tracing.chatbot.workflows import ChatbotWorkflow
from tests.langsmith_tracing.helpers import make_text_response, poll_last_response


def _make_function_call_response(
    name: str, arguments: dict, call_id: str = "call_123"
) -> Response:
    return Response.model_construct(
        id="resp_tool",
        created_at=0.0,
        model="gpt-4o-mini",
        object="response",
        output=[
            ResponseFunctionToolCall.model_construct(
                id="fc_mock",
                type="function_call",
                name=name,
                arguments=json.dumps(arguments),
                call_id=call_id,
                status="completed",
            )
        ],
        parallel_tool_calls=False,
        tool_choice="auto",
        tools=[],
    )


async def test_chatbot_save_note(client: Client, env: WorkflowEnvironment):
    call_count = 0

    @activity.defn(name="call_openai")
    async def mock_call_openai(request: OpenAIRequest) -> Response:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return _make_function_call_response(
                name="save_note",
                arguments={"name": "greeting", "content": "Hello world"},
            )
        return make_text_response("Note saved successfully!")

    @activity.defn(name="save_note")
    async def mock_save_note(request: NoteRequest) -> str:
        return f"Saved note '{request.name}'."

    @activity.defn(name="read_note")
    async def mock_read_note(request: NoteRequest) -> str:
        return request.content

    async with Worker(
        client,
        task_queue="test-langsmith-chatbot",
        workflows=[ChatbotWorkflow],
        activities=[mock_call_openai, mock_save_note, mock_read_note],
        plugins=[LangSmithPlugin()],
    ):
        wf_handle = await client.start_workflow(
            ChatbotWorkflow.run,
            id=f"test-chatbot-{uuid.uuid4().hex[:8]}",
            task_queue="test-langsmith-chatbot",
        )

        await wf_handle.signal(ChatbotWorkflow.user_message, "Save a note")
        response = await poll_last_response(wf_handle, ChatbotWorkflow.last_response)
        assert response == "Note saved successfully!"

        notes = await wf_handle.query(ChatbotWorkflow.notes)
        assert notes == {"greeting": "Hello world"}

        await wf_handle.signal(ChatbotWorkflow.exit)
        result = await wf_handle.result()
        assert result == "Session ended."


async def test_chatbot_read_note(client: Client, env: WorkflowEnvironment):
    """Test that read_note calls an activity with content from workflow state."""
    call_count = 0

    @activity.defn(name="call_openai")
    async def mock_call_openai(request: OpenAIRequest) -> Response:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return _make_function_call_response(
                name="save_note",
                arguments={"name": "todo", "content": "Buy milk"},
                call_id="call_save",
            )
        if call_count == 2:
            return make_text_response("Saved your todo!")
        if call_count == 3:
            return _make_function_call_response(
                name="read_note",
                arguments={"name": "todo"},
                call_id="call_read",
            )
        return make_text_response("Your todo says: Buy milk")

    @activity.defn(name="save_note")
    async def mock_save_note(request: NoteRequest) -> str:
        return f"Saved note '{request.name}'."

    @activity.defn(name="read_note")
    async def mock_read_note(request: NoteRequest) -> str:
        return request.content

    async with Worker(
        client,
        task_queue="test-langsmith-chatbot-read",
        workflows=[ChatbotWorkflow],
        activities=[mock_call_openai, mock_save_note, mock_read_note],
        plugins=[LangSmithPlugin()],
    ):
        wf_handle = await client.start_workflow(
            ChatbotWorkflow.run,
            id=f"test-chatbot-read-{uuid.uuid4().hex[:8]}",
            task_queue="test-langsmith-chatbot-read",
        )

        await wf_handle.signal(ChatbotWorkflow.user_message, "Save my todo")
        response = await poll_last_response(wf_handle, ChatbotWorkflow.last_response)
        assert response == "Saved your todo!"

        await wf_handle.signal(ChatbotWorkflow.user_message, "Read my todo")
        new_response = await poll_last_response(
            wf_handle, ChatbotWorkflow.last_response, prev_response=response
        )
        assert new_response == "Your todo says: Buy milk"

        await wf_handle.signal(ChatbotWorkflow.exit)
        await wf_handle.result()
