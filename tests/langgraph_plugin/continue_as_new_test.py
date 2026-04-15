import uuid
from datetime import timedelta

from temporalio.client import Client
from temporalio.contrib.langgraph import LangGraphPlugin
from temporalio.worker import Worker

from langgraph_plugin.graph_api.continue_as_new.workflow import (
    PipelineInput,
    PipelineWorkflow,
    build_graph,
)


async def test_continue_as_new_graph_api(client: Client) -> None:
    """Input 10: 10*2=20 -> 20+50=70 -> 70*3=210."""
    task_queue = f"continue-as-new-test-{uuid.uuid4()}"
    plugin = LangGraphPlugin(graphs={"pipeline": build_graph()})

    async with Worker(
        client,
        task_queue=task_queue,
        workflows=[PipelineWorkflow],
        plugins=[plugin],
    ):
        result = await client.execute_workflow(
            PipelineWorkflow.run,
            PipelineInput(data=10),
            id=f"continue-as-new-{uuid.uuid4()}",
            task_queue=task_queue,
            execution_timeout=timedelta(seconds=60),
        )

    assert result == 210
