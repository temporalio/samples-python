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
                print(text, end="", flush=True)

    consume_task = asyncio.create_task(consume())
    result = await handle.result()
    print()

    # The workflow has completed; give the subscriber a beat to drain, then stop.
    consume_task.cancel()
    try:
        await consume_task
    except asyncio.CancelledError:
        pass

    print(f"Final result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
