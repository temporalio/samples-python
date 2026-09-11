import uuid

from temporalio.client import Client
from temporalio.worker import Worker

from pydantic_ai_plugin.structured_output.workflow import (
    IncidentSummary,
    StructuredInput,
    StructuredOutputWorkflow,
)
from tests.pydantic_ai_plugin.helpers import with_pydantic_ai


async def test_structured_output_crosses_workflow_boundary(client: Client) -> None:
    client = with_pydantic_ai(client)
    task_queue = f"pydantic-ai-structured-{uuid.uuid4()}"
    async with Worker(
        client,
        task_queue=task_queue,
        workflows=[StructuredOutputWorkflow],
        max_cached_workflows=0,
    ):
        result = await client.execute_workflow(
            StructuredOutputWorkflow.run,
            StructuredInput(prompt="Summarize the incident."),
            id=f"pydantic-ai-structured-{uuid.uuid4()}",
            task_queue=task_queue,
        )

    assert result == IncidentSummary(
        service="payments",
        severity=2,
        action="Restart the worker pool.",
    )
