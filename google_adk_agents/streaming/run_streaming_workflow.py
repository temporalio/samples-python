import asyncio
from datetime import timedelta

from google.adk.models.llm_response import LlmResponse
from temporalio.client import Client
from temporalio.contrib.google_adk_agents import GoogleAdkPlugin
from temporalio.contrib.workflow_streams import WorkflowStreamClient

from google_adk_agents.streaming.workflows.streaming_workflow import (
    StreamingAgentWorkflow,
)

WORKFLOW_ID = "google-adk-agents-streaming-workflow-id"


async def main():
    client = await Client.connect("localhost:7233", plugins=[GoogleAdkPlugin()])

    # Start the workflow (don't await its result yet) so we can subscribe to
    # its stream while it runs.
    handle = await client.start_workflow(
        StreamingAgentWorkflow.run,
        "Tell me a short story about a robot learning to paint.",
        id=WORKFLOW_ID,
        task_queue="google-adk-agents-streaming",
    )

    # Subscribe to the "responses" topic and print text chunks as they arrive.
    stream = WorkflowStreamClient.create(client, WORKFLOW_ID)

    async def print_chunks() -> None:
        print("Streaming response:")
        async for item in stream.subscribe(
            ["responses"],
            from_offset=0,
            result_type=LlmResponse,
            poll_cooldown=timedelta(milliseconds=50),
        ):
            response = item.data
            if response.content and response.content.parts:
                for part in response.content.parts:
                    if part.text:
                        print(part.text, end="", flush=True)

    chunk_task = asyncio.create_task(print_chunks())
    result = await handle.result()
    chunk_task.cancel()
    try:
        await chunk_task
    except asyncio.CancelledError:
        pass

    print(f"\n\nFinal result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
