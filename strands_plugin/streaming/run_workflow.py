"""Start the streaming workflow and consume model events live."""

# @@@SNIPSTART python-strands-streaming-client
import asyncio
import os
from datetime import timedelta

from strands.types.streaming import StreamEvent
from temporalio.client import Client
from temporalio.contrib.workflow_streams import WorkflowStreamClient

from strands_plugin.streaming.workflow import StreamingWorkflow


async def main() -> None:
    client = await Client.connect(os.environ.get("TEMPORAL_ADDRESS", "localhost:7233"))
    workflow_id = "strands-streaming"

    handle = await client.start_workflow(
        StreamingWorkflow.run,
        "Count from 1 to 5, one number per sentence.",
        id=workflow_id,
        task_queue="strands-streaming",
    )

    async def consume() -> None:
        stream = WorkflowStreamClient.create(client, workflow_id)
        async for item in stream.subscribe(
            ["events"],
            from_offset=0,
            result_type=StreamEvent,
            poll_cooldown=timedelta(milliseconds=50),
        ):
            event: StreamEvent = item.data
            if "contentBlockDelta" in event:
                delta = event["contentBlockDelta"].get("delta", {})
                if "text" in delta:
                    print(delta["text"], end="", flush=True)
            elif "messageStop" in event:
                print()
                return

    consume_task = asyncio.create_task(consume())
    result = await handle.result()
    await asyncio.wait_for(consume_task, timeout=10.0)
    print(f"Final result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
# @@@SNIPEND
