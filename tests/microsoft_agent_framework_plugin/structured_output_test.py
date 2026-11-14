import uuid

from temporalio.client import Client
from temporalio.worker import Worker

from microsoft_agent_framework_plugin.structured_output.workflow import (
    PersonInfo,
    StructuredOutputWorkflow,
)
from tests.microsoft_agent_framework_plugin._fake_chat_client import scripted_plugin
from tests.microsoft_agent_framework_plugin.helpers import (
    INVOKE_MODEL,
    count_scheduled_activities,
    with_plugin,
)


async def test_structured_output(client: Client) -> None:
    plugin, factory = scripted_plugin(
        ['{"name": "John Smith", "age": 30, "occupation": "software engineer"}']
    )
    client = with_plugin(client, plugin)
    task_queue = f"microsoft-agent-framework-structured-output-{uuid.uuid4()}"

    async with Worker(
        client,
        task_queue=task_queue,
        workflows=[StructuredOutputWorkflow],
        max_cached_workflows=0,
    ):
        handle = await client.start_workflow(
            StructuredOutputWorkflow.run,
            "John Smith is a 30 year-old software engineer.",
            id=f"microsoft-agent-framework-structured-output-{uuid.uuid4()}",
            task_queue=task_queue,
        )
        result = await handle.result()

    # The Pydantic model crossed the Workflow boundary through the plugin's converter.
    assert result == PersonInfo(
        name="John Smith", age=30, occupation="software engineer"
    )
    assert await count_scheduled_activities(handle) == {INVOKE_MODEL: 1}
    # The model Activity received the schema, not the class.
    (call,) = factory().calls
    assert call["options"]["response_format"]["json_schema"]["name"] == "PersonInfo"
