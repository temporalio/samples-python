"""Start the streaming workflow and print model chunks live.

Subscribes to the workflow-streams topic the streaming activity publishes to and
renders each chunk's text as it arrives. Each published item is an
``AIMessageChunk`` in ``langchain_core.load.dumpd`` form, so it is reconstructed
with ``langchain_core.load.load``. The final aggregated message is also returned
as the workflow result (identical to the non-streaming path).
"""

import asyncio
import os
from datetime import timedelta

from langchain_core.load import load
from temporalio.client import Client
from temporalio.contrib.workflow_streams import WorkflowStreamClient

from deepagents_plugin.streaming.workflow import STREAMING_TOPIC, StreamingWorkflow


async def main() -> None:
    client = await Client.connect(os.environ.get("TEMPORAL_ADDRESS", "localhost:7233"))
    workflow_id = "deepagents-streaming"

    handle = await client.start_workflow(
        StreamingWorkflow.run,
        "Write a short paragraph about durable execution.",
        id=workflow_id,
        task_queue="deepagents-streaming",
    )

    printed: list[str] = []

    async def consume() -> None:
        stream = WorkflowStreamClient.create(client, workflow_id)
        async for item in stream.subscribe(
            [STREAMING_TOPIC],
            from_offset=0,
            result_type=dict,
            poll_cooldown=timedelta(milliseconds=50),
        ):
            chunk = load(item.data)
            text = getattr(chunk, "content", "")
            if text:
                printed.append(str(text))
                print(text, end="", flush=True)

    consume_task = asyncio.create_task(consume())
    result = await handle.result()

    # The workflow has completed, but the subscriber may still be catching up on
    # the tail of the stream. The streamed chunks add up to the durable result,
    # so drain until all of it has been printed; the timeout only bounds a
    # regression, it never gates the happy path.
    async def drained() -> None:
        while result not in "".join(printed):
            await asyncio.sleep(0.05)

    try:
        await asyncio.wait_for(drained(), timeout=10.0)
    except asyncio.TimeoutError:
        print("\n(timed out waiting for the subscriber to drain the stream)")
    consume_task.cancel()
    try:
        await consume_task
    except asyncio.CancelledError:
        pass

    print()
    print(f"Final result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
