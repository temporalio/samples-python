import uuid

from langchain_core.messages import AIMessage
from temporalio.client import Client
from temporalio.contrib.deepagents import DeepAgentsPlugin
from temporalio.contrib.deepagents.testing import mock_model_provider
from temporalio.worker import Worker

from deepagents_plugin.subagents.workflow import SubagentsWorkflow
from tests.deepagents_plugin.helpers import INVOKE_MODEL, count_scheduled_activities


async def test_subagents(client: Client) -> None:
    # Script the delegation end-to-end: the coordinator calls the built-in
    # `task` tool, the researcher sub-agent (sharing the provider's response
    # queue) reports findings, and the coordinator synthesizes them. This
    # exercises the scenario's headline — durability propagating across the
    # agent tree — rather than letting the coordinator answer in one turn.
    delegate = AIMessage(
        content="",
        tool_calls=[
            {
                "name": "task",
                "args": {
                    "description": (
                        "Research how Temporal handles workflow retries and "
                        "report your findings."
                    ),
                    "subagent_type": "researcher",
                },
                "id": "call-task",
            }
        ],
    )
    findings = AIMessage(
        content="Findings: retries are governed by per-activity RetryPolicy."
    )
    final = AIMessage(
        content="Coordinated research answer: Temporal retries are policy-driven."
    )
    plugin = DeepAgentsPlugin(
        model_provider=mock_model_provider([delegate, findings, final]),
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
        handle = await client.start_workflow(
            SubagentsWorkflow.run,
            "Investigate durable execution and report back.",
            id=f"deepagents-subagents-{uuid.uuid4()}",
            task_queue=task_queue,
        )
        result = await handle.result()

    assert "Coordinated" in result
    # Three model activities prove the delegation really ran: the coordinator's
    # delegating turn, the researcher's turn, and the synthesis turn — the
    # sub-agent's model call became an activity with no per-sub-agent wiring.
    counts = await count_scheduled_activities(handle)
    assert counts[INVOKE_MODEL] >= 3, counts
