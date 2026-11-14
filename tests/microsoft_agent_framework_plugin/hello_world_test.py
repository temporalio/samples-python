import uuid

from temporalio.client import Client
from temporalio.worker import Worker

from microsoft_agent_framework_plugin.hello_world.workflow import HelloWorldWorkflow
from tests.microsoft_agent_framework_plugin._fake_chat_client import scripted_plugin
from tests.microsoft_agent_framework_plugin.helpers import (
    INVOKE_MODEL,
    count_scheduled_activities,
    with_plugin,
)


async def test_hello_world(client: Client) -> None:
    # A scripted model, so the test runs offline with no OPENAI_API_KEY.
    plugin, factory = scripted_plugin(["Workflows outlive crashes."])
    client = with_plugin(client, plugin)
    task_queue = f"microsoft-agent-framework-hello-world-{uuid.uuid4()}"

    async with Worker(
        client,
        task_queue=task_queue,
        workflows=[HelloWorldWorkflow],
        max_cached_workflows=0,
    ):
        handle = await client.start_workflow(
            HelloWorldWorkflow.run,
            "Write a haiku.",
            id=f"microsoft-agent-framework-hello-world-{uuid.uuid4()}",
            task_queue=task_queue,
        )
        result = await handle.result()

    assert result == "Workflows outlive crashes."
    # The model call ran as the plugin's Activity, not inside the Workflow.
    assert await count_scheduled_activities(handle) == {INVOKE_MODEL: 1}
    (call,) = factory().calls
    assert call["options"]["instructions"] == "You are a concise assistant."
    assert call["messages"][-1].text == "Write a haiku."
