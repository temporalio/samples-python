import json
import uuid

from temporalio import activity
from temporalio.client import Client
from temporalio.contrib.langsmith import LangSmithPlugin
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from langsmith_tracing.chatbot.activities import ChatResponse, OpenAIRequest, ToolCall
from langsmith_tracing.chatbot.workflows import ChatbotWorkflow
from tests.langsmith_tracing.helpers import make_text_response


def _make_function_call_response(
    name: str, arguments: dict, call_id: str = "call_123"
) -> ChatResponse:
    return ChatResponse(
        id="resp_tool",
        tool_calls=[
            ToolCall(
                call_id=call_id,
                name=name,
                arguments=json.dumps(arguments),
            )
        ],
    )


async def test_chatbot_save_note(client: Client, env: WorkflowEnvironment):
    """Test save_note tool call loop — save_note runs as a workflow method."""
    call_count = 0

    @activity.defn(name="call_openai")
    async def mock_call_openai(request: OpenAIRequest) -> ChatResponse:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return _make_function_call_response(
                name="save_note",
                arguments={"name": "greeting", "content": "Hello world"},
            )
        return make_text_response("Note saved successfully!")

    async with Worker(
        client,
        task_queue="test-langsmith-chatbot",
        workflows=[ChatbotWorkflow],
        activities=[mock_call_openai],
        plugins=[LangSmithPlugin()],
    ):
        wf_handle = await client.start_workflow(
            ChatbotWorkflow.run,
            id=f"test-chatbot-{uuid.uuid4().hex[:8]}",
            task_queue="test-langsmith-chatbot",
        )

        response = await wf_handle.execute_update(
            ChatbotWorkflow.message_from_user, "Save a note"
        )
        assert response == "Note saved successfully!"

        notes = await wf_handle.query(ChatbotWorkflow.notes)
        assert notes == {"greeting": "Hello world"}

        await wf_handle.signal(ChatbotWorkflow.exit)
        result = await wf_handle.result()
        assert result == "Session ended."


async def test_chatbot_read_note(client: Client, env: WorkflowEnvironment):
    """Test read_note tool call loop — read_note runs as a workflow method."""
    call_count = 0

    @activity.defn(name="call_openai")
    async def mock_call_openai(request: OpenAIRequest) -> ChatResponse:
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

    async with Worker(
        client,
        task_queue="test-langsmith-chatbot-read",
        workflows=[ChatbotWorkflow],
        activities=[mock_call_openai],
        plugins=[LangSmithPlugin()],
    ):
        wf_handle = await client.start_workflow(
            ChatbotWorkflow.run,
            id=f"test-chatbot-read-{uuid.uuid4().hex[:8]}",
            task_queue="test-langsmith-chatbot-read",
        )

        response = await wf_handle.execute_update(
            ChatbotWorkflow.message_from_user, "Save my todo"
        )
        assert response == "Saved your todo!"

        response = await wf_handle.execute_update(
            ChatbotWorkflow.message_from_user, "Read my todo"
        )
        assert response == "Your todo says: Buy milk"

        await wf_handle.signal(ChatbotWorkflow.exit)
        await wf_handle.result()
