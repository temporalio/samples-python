import uuid
from typing import Any

from temporalio import workflow
from temporalio.client import Client, WorkflowExecutionStatus
from temporalio.contrib.deepagents import DeepAgentsPlugin, run_deep_agent
from temporalio.contrib.deepagents.testing import mock_model_provider
from temporalio.worker import Worker

from deepagents_plugin.continue_as_new.workflow import LongResearchAgent


async def test_continue_as_new(client: Client) -> None:
    # The sample defers to the server-suggested mode, which a short scripted
    # run never triggers, so this exercises the run_deep_agent contract on the
    # real sample workflow without a continue-as-new. The first arg is the
    # messages mapping (the run_deep_agent contract), not a bare string.
    plugin = DeepAgentsPlugin(
        model_provider=mock_model_provider(["The research is complete: done."]),
    )
    task_queue = f"deepagents-continue-as-new-{uuid.uuid4()}"

    config = client.config()
    config["plugins"] = [*config["plugins"], plugin]
    client = Client(**config)

    async with Worker(
        client,
        task_queue=task_queue,
        workflows=[LongResearchAgent],
        max_cached_workflows=0,
    ):
        result = await client.execute_workflow(
            LongResearchAgent.run,
            {"messages": [{"role": "user", "content": "Summarize durable execution."}]},
            id=f"deepagents-continue-as-new-{uuid.uuid4()}",
            task_queue=task_queue,
        )

    assert "complete" in result


class _ScriptedAgent:
    """A stand-in compiled agent that appends one message per turn and keeps a
    todo pending until the conversation grows, forcing continue-as-new.

    It is not a LangChain object — it just satisfies the ``ainvoke`` shape that
    ``run_deep_agent`` drives, so the continue-as-new path is exercised without a
    model provider or the LangChain import tree.
    """

    async def ainvoke(self, input: Any) -> dict:
        messages = list(input.get("messages", [])) if isinstance(input, dict) else []
        messages = [*messages, "step"]
        done = len(messages) >= 3
        return {
            "messages": messages,
            "todos": [
                {"content": "research", "status": "completed" if done else "pending"}
            ],
        }


@workflow.defn
class _ContinueAsNewProbe:
    @workflow.run
    async def run(self, input: dict, state_snapshot: dict | None = None) -> dict:
        # Threshold of 1 continues-as-new as soon as there is pending work.
        # ``input`` is threaded straight through, exactly as LongResearchAgent
        # does — re-wrapping it would nest a dict where a message is expected and
        # corrupt the carried conversation.
        return await run_deep_agent(
            _ScriptedAgent(),
            input,
            continue_as_new_after=1,
            state_snapshot=state_snapshot,
        )


async def test_continue_as_new_carries_conversation(client: Client) -> None:
    # Low threshold + persistent pending work actually triggers
    # workflow.continue_as_new, so this guards the scenario's headline feature:
    # the carried conversation must survive the boundary well-formed.
    plugin = DeepAgentsPlugin()
    task_queue = f"deepagents-continue-as-new-probe-{uuid.uuid4()}"

    config = client.config()
    config["plugins"] = [*config["plugins"], plugin]
    client = Client(**config)

    async with Worker(
        client,
        task_queue=task_queue,
        workflows=[_ContinueAsNewProbe],
        max_cached_workflows=0,
    ):
        handle = await client.start_workflow(
            _ContinueAsNewProbe.run,
            {"messages": ["start"]},
            id=f"deepagents-continue-as-new-probe-{uuid.uuid4()}",
            task_queue=task_queue,
        )
        result = await handle.result()

    # Reaching >= 3 messages is only possible if each pre-continue-as-new
    # snapshot was carried into the continued run and merged. Every carried
    # message stays a plain string — no nested-dict corruption from re-wrapping
    # the input across the boundary.
    assert len(result["messages"]) >= 3, result
    assert all(isinstance(m, str) for m in result["messages"]), result
    assert result["todos"][0]["status"] == "completed"
    # The boundary really happened: a loop-in-one-run implementation would
    # produce the same final result, so pin the FIRST run's close event.
    first = client.get_workflow_handle(handle.id, run_id=handle.first_execution_run_id)
    desc = await first.describe()
    assert desc.status == WorkflowExecutionStatus.CONTINUED_AS_NEW, desc.status
