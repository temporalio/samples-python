"""Start the streaming workflow and consume model chunks live."""

# @@@SNIPSTART python-google-genai-streaming-run-workflow
import asyncio
import os
from datetime import timedelta

from google.genai import types
from temporalio.client import Client
from temporalio.contrib.workflow_streams import WorkflowStreamClient

from google_genai_plugin.streaming.workflow import StreamingWorkflow


async def main() -> None:
    client = await Client.connect(os.environ.get("TEMPORAL_ADDRESS", "localhost:7233"))
    workflow_id = "google-genai-streaming"

    handle = await client.start_workflow(
        StreamingWorkflow.run,
        "Count from 1 to 5, one number per sentence.",
        id=workflow_id,
        task_queue="google-genai-streaming",
    )

    # Subscribe to the "gemini" topic and print chunks as the model produces them.
    stream = WorkflowStreamClient.create(client, workflow_id)
    async for item in stream.subscribe(
        ["gemini"],
        from_offset=0,
        result_type=types.GenerateContentResponse,
        poll_cooldown=timedelta(milliseconds=50),
    ):
        chunk: types.GenerateContentResponse = item.data
        if chunk.text:
            print(chunk.text, end="", flush=True)
        if chunk.candidates and chunk.candidates[0].finish_reason:
            print()
            break

    # Release the workflow now that we've consumed the stream.
    await handle.signal(StreamingWorkflow.finish)
    result = await handle.result()
    print(f"Final result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
# @@@SNIPEND
