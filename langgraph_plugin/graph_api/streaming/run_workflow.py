"""Start the streaming workflow and subscribe to its Workflow Stream (Graph API)."""

import asyncio
import os
from datetime import timedelta

from temporalio.client import Client
from temporalio.contrib.workflow_streams import WorkflowStreamClient

from langgraph_plugin.graph_api.streaming.workflow import StreamingWorkflow


async def main() -> None:
    client = await Client.connect(os.environ.get("TEMPORAL_ADDRESS", "localhost:7233"))

    handle = await client.start_workflow(
        StreamingWorkflow.run,
        "a brave robot",
        id="streaming-workflow",
        task_queue="langgraph-streaming",
    )

    # Subscribe to all topics on the workflow's stream and demultiplex on topic.
    ws = WorkflowStreamClient.create(client, handle.id)
    async for item in ws.subscribe(
        from_offset=0,
        result_type=dict,
        poll_cooldown=timedelta(milliseconds=50),
    ):
        if item.topic == "tokens":
            print(item.data["token"], end="", flush=True)
        elif item.topic == "progress":
            if item.data.get("done"):
                # Let the workflow know we are done consuming so it can complete.
                await handle.signal(StreamingWorkflow.ack_stream)
                break
            print(f"\n[progress] {item.data}")

    result = await handle.result()
    print(f"\n\nFinal result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
