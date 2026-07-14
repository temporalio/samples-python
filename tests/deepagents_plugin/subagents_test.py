import uuid

from temporalio.client import Client
from temporalio.contrib.deepagents import DeepAgentsPlugin
from temporalio.contrib.deepagents.testing import mock_model_provider
from temporalio.worker import Worker

from deepagents_plugin.subagents.workflow import SubagentsWorkflow


async def test_subagents(client: Client) -> None:
    # The coordinator and its researcher sub-agent share the durable model object,
    # so every model call routes through an activity with no per-sub-agent wiring.
    # A scripted model keeps the run offline; we assert the tree runs to a result.
    plugin = DeepAgentsPlugin(
        model_provider=mock_model_provider(["Coordinated research answer."]),
    )
    task_queue = f"deepagents-subagents-{uuid.uuid4()}"

    config = client.config()
    config["plugins"] = [*config["plugins"], plugin]
    client = Client(**config)

    async with Worker(
        client,
        task_queue=task_queue,
        workflows=[SubagentsWorkflow],
        max_cached_workflows=0,
    ):
        result = await client.execute_workflow(
            SubagentsWorkflow.run,
            "Investigate durable execution and report back.",
            id=f"deepagents-subagents-{uuid.uuid4()}",
            task_queue=task_queue,
        )

    assert "Coordinated" in result
