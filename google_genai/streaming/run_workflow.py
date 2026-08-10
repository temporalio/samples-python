"""Start the streaming workflow and consume model chunks live."""

import asyncio
import os
from datetime import timedelta

from google.genai import types
from temporalio.client import Client
from temporalio.contrib.pydantic import pydantic_data_converter
from temporalio.contrib.workflow_streams import WorkflowStreamClient

from google_genai.streaming.workflow import StreamingWorkflow

# Only a chunk carrying finish_reason ends the subscribe loop, so bound the
# wait: if generation fails mid-stream, no such chunk ever arrives.
STREAM_TIMEOUT = 60.0


# @@@SNIPSTART python-google-genai-streaming-run-workflow
async def consume(client: Client, workflow_id: str) -> None:
    """Subscribe to the "gemini" topic and print chunks as the model produces them."""
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
            return


async def main() -> None:
    # The stream publishes Pydantic GenerateContentResponse chunks, so the
    # consumer needs the Pydantic data converter to decode them.
    client = await Client.connect(
        os.environ.get("TEMPORAL_ADDRESS", "localhost:7233"),
        data_converter=pydantic_data_converter,
    )
    # @@@SNIPEND
    workflow_id = "google-genai-streaming"

    handle = await client.start_workflow(
        StreamingWorkflow.run,
        "Count from 1 to 5, one number per sentence.",
        id=workflow_id,
        task_queue="google-genai-streaming",
    )

    try:
        await asyncio.wait_for(consume(client, workflow_id), timeout=STREAM_TIMEOUT)
    except asyncio.TimeoutError:
        print(f"\nNo end-of-stream chunk after {STREAM_TIMEOUT}s; giving up.")

    # Release the workflow now that we've consumed the stream.
    await handle.signal(StreamingWorkflow.finish)
    result = await handle.result()
    print(f"Final result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
