"""Start the streaming workflow and print the model's updates as they arrive."""

# @@@SNIPSTART python-agent-framework-streaming-client
import asyncio
import os
from datetime import timedelta

from agent_framework import ChatResponseUpdate
from temporalio.client import Client
from temporalio.contrib.workflow_streams import WorkflowStreamClient

from agent_framework_plugin.streaming.workflow import STREAMING_TOPIC, StreamingWorkflow


async def main() -> None:
    client = await Client.connect(os.environ.get("TEMPORAL_ADDRESS", "localhost:7233"))
    workflow_id = "agent-framework-streaming"

    handle = await client.start_workflow(
        StreamingWorkflow.run,
        "Count from 1 to 5, one number per sentence.",
        id=workflow_id,
        task_queue="agent-framework-streaming",
    )

    printed: list[str] = []

    async def consume() -> None:
        # Each item is a ChatResponseUpdate in its dict form.
        stream = WorkflowStreamClient.create(client, workflow_id)
        async for item in stream.subscribe(
            [STREAMING_TOPIC],
            from_offset=0,
            result_type=dict,
            poll_cooldown=timedelta(milliseconds=50),
        ):
            update = ChatResponseUpdate.from_dict(item.data)
            if update.text:
                printed.append(update.text)
                print(update.text, end="", flush=True)

    consume_task = asyncio.create_task(consume())
    result = await handle.result()

    # The subscriber may still be reading the tail of the stream after the
    # Workflow completes. The streamed text adds up to the result, so wait for it.
    async def drained() -> None:
        while result not in "".join(printed):
            await asyncio.sleep(0.05)

    try:
        await asyncio.wait_for(drained(), timeout=10)
    except asyncio.TimeoutError:
        print("\n(timed out waiting for the last streamed updates)")
    consume_task.cancel()
    try:
        await consume_task
    except asyncio.CancelledError:
        pass

    print()
    print(f"Final result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
# @@@SNIPEND
