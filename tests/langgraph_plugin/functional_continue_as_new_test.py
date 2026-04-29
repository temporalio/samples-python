import sys
import uuid
from datetime import timedelta

import pytest
from temporalio.client import Client
from temporalio.contrib.langgraph import LangGraphPlugin
from temporalio.worker import Worker

from langgraph_plugin.functional_api.continue_as_new.workflow import (
    PipelineFunctionalWorkflow,
    PipelineInput,
    activity_options,
    all_tasks,
    pipeline_entrypoint,
)

pytestmark = pytest.mark.skipif(
    sys.version_info < (3, 11),
    reason="LangGraph Functional API requires Python >= 3.11 for async context propagation",
)


async def test_functional_continue_as_new(client: Client) -> None:
    """Input 10: 10*2=20 -> 20+50=70 -> 70*3=210."""
    task_queue = f"functional-continue-test-{uuid.uuid4()}"
    plugin = LangGraphPlugin(
        entrypoints={"pipeline": pipeline_entrypoint},
        tasks=all_tasks,
        activity_options=activity_options,
    )

    async with Worker(
        client,
        task_queue=task_queue,
        workflows=[PipelineFunctionalWorkflow],
        plugins=[plugin],
    ):
        result = await client.execute_workflow(
            PipelineFunctionalWorkflow.run,
            PipelineInput(data=10),
            id=f"functional-continue-{uuid.uuid4()}",
            task_queue=task_queue,
            execution_timeout=timedelta(seconds=60),
        )

    assert result == {"result": 210}
