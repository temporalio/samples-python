import uuid
from typing import Any

import pytest
import pytest_asyncio
from temporalio.claude_agent_sdk import ClaudeAgentSDKPlugin
from temporalio.client import Client, WorkflowFailureError, WorkflowHandle
from temporalio.contrib.pydantic import pydantic_data_converter
from temporalio.exceptions import ApplicationError
from temporalio.worker import Replayer, Worker

from claude_agent_sdk_plugin.offline import ScriptedApi, scripted_api, tool_use
from claude_agent_sdk_plugin.structured_output.workflow import (
    SupportTicket,
    TriageTicketWorkflow,
)

MESSAGE = "The app crashes every time I open the settings page."
TICKET = SupportTicket(category="bug", priority=2, summary="Settings page crashes")


@pytest_asyncio.fixture
async def pydantic_client(client: Client) -> Client:
    config = client.config()
    config["data_converter"] = pydantic_data_converter
    return Client(**config)


async def triage(
    client: Client, answers: dict[str, Any]
) -> tuple[ScriptedApi, WorkflowHandle[Any, SupportTicket]]:
    task_queue = f"claude-agent-sdk-structured-output-{uuid.uuid4()}"
    with scripted_api(answers) as api:
        async with Worker(
            client,
            task_queue=task_queue,
            workflows=[TriageTicketWorkflow],
            plugins=[ClaudeAgentSDKPlugin()],
        ):
            handle = await client.start_workflow(
                TriageTicketWorkflow.run,
                MESSAGE,
                id=f"structured-output-{uuid.uuid4()}",
                task_queue=task_queue,
            )
            await handle.result()
    return api, handle


async def test_returns_validated_model(pydantic_client: Client) -> None:
    api, handle = await triage(
        pydantic_client,
        {
            "Triage this customer message": tool_use(
                "toolu_1", "StructuredOutput", **TICKET.model_dump()
            )
        },
    )

    assert await handle.result() == TICKET

    schema_tool = next(
        tool for tool in api.requests[0]["tools"] if tool["name"] == "StructuredOutput"
    )
    assert schema_tool["input_schema"] == SupportTicket.model_json_schema()

    await Replayer(
        workflows=[TriageTicketWorkflow], plugins=[ClaudeAgentSDKPlugin()]
    ).replay_workflow(await handle.fetch_history())


async def test_claude_code_returns_schema_errors_to_the_model(
    pydantic_client: Client,
) -> None:
    api, handle = await triage(
        pydantic_client,
        {
            "Triage this customer message": tool_use(
                "toolu_1", "StructuredOutput", **{**TICKET.model_dump(), "priority": 9}
            ),
            "tool_result:toolu_1": tool_use(
                "toolu_2", "StructuredOutput", **TICKET.model_dump()
            ),
        },
    )

    assert await handle.result() == TICKET
    assert api.asked == ["Triage this customer message", "tool_result:toolu_1"]
    schema_error = next(
        block
        for request in api.requests
        for message in request["messages"]
        if message["role"] == "user" and not isinstance(message["content"], str)
        for block in message["content"]
        if block["type"] == "tool_result"
    )
    assert schema_error["is_error"]
    assert "priority: must be <= 5" in schema_error["content"]


async def test_workflow_fails_without_structured_output(
    pydantic_client: Client,
) -> None:
    with pytest.raises(WorkflowFailureError) as failure:
        await triage(
            pydantic_client,
            {
                "Triage this customer message": "I cannot triage this.",
                "structured-output-enforce": "I still cannot triage this.",
            },
        )

    cause = failure.value.cause
    assert isinstance(cause, ApplicationError)
    assert cause.message == "Claude Code returned no structured output"
    assert cause.non_retryable
