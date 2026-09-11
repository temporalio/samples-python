import uuid

from temporalio.client import Client
from temporalio.worker import Worker

from pydantic_ai_plugin.tools.workflow import ToolsInput, ToolsWorkflow
from tests.pydantic_ai_plugin.helpers import with_pydantic_ai


async def test_tool_execution_boundaries(client: Client) -> None:
    client = with_pydantic_ai(client)
    task_queue = f"pydantic-ai-tools-{uuid.uuid4()}"
    async with Worker(
        client,
        task_queue=task_queue,
        workflows=[ToolsWorkflow],
        max_cached_workflows=0,
    ):
        handle = await client.start_workflow(
            ToolsWorkflow.run,
            ToolsInput(prompt="Use both tools."),
            id=f"pydantic-ai-tools-{uuid.uuid4()}",
            task_queue=task_queue,
        )
        assert await handle.result() == "Both checks completed."

    activity_names = []
    async for event in handle.fetch_history_events():
        if event.HasField("activity_task_scheduled_event_attributes"):
            attributes = event.activity_task_scheduled_event_attributes
            activity_names.append(attributes.activity_type.name)

    tool_activities = [name for name in activity_names if name.endswith("__call_tool")]
    assert len(tool_activities) == 1
