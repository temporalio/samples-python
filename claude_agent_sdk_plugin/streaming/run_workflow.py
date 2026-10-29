import asyncio
import os
import sys

from temporalio.client import Client
from temporalio.contrib.workflow_streams import WorkflowStreamClient

from claude_agent_sdk_plugin.streaming.workflow import StreamingWorkflow

DEFAULT_PROMPT = "Count from one to five, one number per sentence."


async def main() -> None:
    client = await Client.connect(os.environ.get("TEMPORAL_ADDRESS", "localhost:7233"))
    workflow_id = "claude-agent-sdk-streaming"

    handle = await client.start_workflow(
        StreamingWorkflow.run,
        " ".join(sys.argv[1:]) or DEFAULT_PROMPT,
        id=workflow_id,
        task_queue="claude-agent-sdk-streaming",
    )

    stream = WorkflowStreamClient.create(client, workflow_id)
    async for item in stream.subscribe(["events"]):
        delta = item.data["event"].get("delta", {})
        if delta.get("type") == "text_delta":
            print(delta["text"], end="", flush=True)

    print(f"\nFinal result: {await handle.result()}")


if __name__ == "__main__":
    asyncio.run(main())
