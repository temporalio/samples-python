import uuid
from datetime import timedelta

from google.genai import types
from temporalio.client import Client
from temporalio.contrib.google_genai.testing import GeminiTestServer, text_response
from temporalio.contrib.workflow_streams import WorkflowStreamClient
from temporalio.worker import Worker

from google_genai_plugin.streaming.workflow import StreamingWorkflow


async def test_streaming_publishes_to_workflow_stream(client: Client) -> None:
    server = GeminiTestServer([text_response("Hello from Gemini stream")])

    config = client.config()
    config["plugins"] = [*config["plugins"], server.plugin()]
    client = Client(**config)

    task_queue = f"google-genai-streaming-{uuid.uuid4()}"
    async with Worker(
        client,
        task_queue=task_queue,
        workflows=[StreamingWorkflow],
        max_cached_workflows=0,
    ):
        wf_id = f"google-genai-streaming-{uuid.uuid4()}"
        handle = await client.start_workflow(
            StreamingWorkflow.run,
            "say hi",
            id=wf_id,
            task_queue=task_queue,
            execution_timeout=timedelta(seconds=15),
        )

        # Consume the published chunk from the "gemini" topic.
        stream = WorkflowStreamClient.create(client, wf_id)
        received: list[types.GenerateContentResponse] = []
        async for item in stream.subscribe(
            ["gemini"],
            from_offset=0,
            result_type=types.GenerateContentResponse,
            poll_cooldown=timedelta(milliseconds=20),
        ):
            received.append(item.data)
            break  # one scripted chunk

        await handle.signal(StreamingWorkflow.finish)
        result = await handle.result()

    assert result == "Hello from Gemini stream"
    assert len(received) == 1
    assert received[0].text == "Hello from Gemini stream"
