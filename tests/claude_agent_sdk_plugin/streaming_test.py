import asyncio
import uuid

from temporalio.claude_agent_sdk import ClaudeAgentSDKPlugin
from temporalio.client import Client, WorkflowHandle
from temporalio.contrib.workflow_streams import WorkflowStreamClient
from temporalio.worker import Replayer, Worker

from claude_agent_sdk_plugin.offline import scripted_api
from claude_agent_sdk_plugin.streaming.workflow import StreamingWorkflow

CHUNKS = ["One. ", "Two. ", "Three. ", "Four. ", "Five."]


async def start(
    client: Client, task_queue: str
) -> WorkflowHandle[StreamingWorkflow, str]:
    return await client.start_workflow(
        StreamingWorkflow.run,
        "Count to five",
        id=f"claude-agent-sdk-streaming-{uuid.uuid4()}",
        task_queue=task_queue,
    )


async def test_subscriber_receives_deltas_in_order(client: Client) -> None:
    task_queue = f"claude-agent-sdk-streaming-{uuid.uuid4()}"
    with scripted_api({"Count": CHUNKS}):
        async with Worker(
            client,
            task_queue=task_queue,
            workflows=[StreamingWorkflow],
            plugins=[ClaudeAgentSDKPlugin()],
        ):
            handle = await start(client, task_queue)
            stream = WorkflowStreamClient.create(client, handle.id)
            deltas = [
                item.data["event"]["delta"]["text"]
                async for item in stream.subscribe(["events"])
                if item.data["event"].get("delta", {}).get("type") == "text_delta"
            ]
            result = await handle.result()

    assert deltas == CHUNKS
    assert "".join(deltas) == result
    await Replayer(
        workflows=[StreamingWorkflow], plugins=[ClaudeAgentSDKPlugin()]
    ).replay_workflow(await handle.fetch_history())


async def test_completes_without_subscriber(client: Client) -> None:
    task_queue = f"claude-agent-sdk-streaming-{uuid.uuid4()}"
    with scripted_api({"Count": CHUNKS}):
        async with Worker(
            client,
            task_queue=task_queue,
            workflows=[StreamingWorkflow],
            plugins=[ClaudeAgentSDKPlugin()],
        ):
            handle = await start(client, task_queue)
            result = await asyncio.wait_for(handle.result(), timeout=60)

    assert result == "".join(CHUNKS)
