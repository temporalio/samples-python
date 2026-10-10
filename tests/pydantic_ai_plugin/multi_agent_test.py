import uuid

from temporalio.client import Client
from temporalio.worker import Worker

from pydantic_ai_plugin.multi_agent.workflow import (
    MultiAgentInput,
    MultiAgentWorkflow,
)
from tests.pydantic_ai_plugin.helpers import with_pydantic_ai


async def test_two_agents_run_durably(client: Client) -> None:
    client = with_pydantic_ai(client)
    task_queue = f"pydantic-ai-multi-agent-{uuid.uuid4()}"
    async with Worker(
        client,
        task_queue=task_queue,
        workflows=[MultiAgentWorkflow],
        max_cached_workflows=0,
    ):
        handle = await client.start_workflow(
            MultiAgentWorkflow.run,
            MultiAgentInput(topic="Temporal recovery"),
            id=f"pydantic-ai-multi-agent-{uuid.uuid4()}",
            task_queue=task_queue,
        )
        result = await handle.result()

    assert result == "A concise explanation is ready."
    activity_names = []
    async for event in handle.fetch_history_events():
        if event.HasField("activity_task_scheduled_event_attributes"):
            attributes = event.activity_task_scheduled_event_attributes
            activity_names.append(attributes.activity_type.name)
    assert any("agent__researcher__model_request" == name for name in activity_names)
    assert any("agent__writer__model_request" == name for name in activity_names)
