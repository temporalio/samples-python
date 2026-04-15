import uuid

from temporalio.client import Client
from temporalio.contrib.langgraph import LangGraphPlugin
from temporalio.worker import Worker

from langgraph_plugin.functional_api.control_flow.workflow import (
    ControlFlowWorkflow,
    activity_options,
    all_tasks,
    control_flow_pipeline,
)


async def test_functional_control_flow(client: Client) -> None:
    task_queue = f"functional-control-flow-test-{uuid.uuid4()}"
    plugin = LangGraphPlugin(
        entrypoints={"control_flow": control_flow_pipeline},
        tasks=all_tasks,
        activity_options=activity_options,
    )

    items = [
        "Fix login bug",
        "URGENT: Production outage",
        "Update README",
        "INVALID:",
        "Urgent: Security patch",
    ]

    async with Worker(
        client,
        task_queue=task_queue,
        workflows=[ControlFlowWorkflow],
        plugins=[plugin],
    ):
        result = await client.execute_workflow(
            ControlFlowWorkflow.run,
            items,
            id=f"functional-control-flow-{uuid.uuid4()}",
            task_queue=task_queue,
        )

    # "INVALID:" should be filtered out
    assert result["total"] == 4
    # Check urgent vs normal routing
    urgent = [r for r in result["results"] if r.startswith("[PRIORITY]")]
    normal = [r for r in result["results"] if r.startswith("[STANDARD]")]
    assert len(urgent) == 2
    assert len(normal) == 2
    assert "2 urgent" in result["summary"]
    assert "2 normal" in result["summary"]
