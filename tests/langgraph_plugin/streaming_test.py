import uuid
from datetime import timedelta
from typing import Any

from temporalio.client import Client
from temporalio.contrib.langgraph import LangGraphPlugin
from temporalio.contrib.workflow_streams import WorkflowStreamClient
from temporalio.worker import Worker

from langgraph_plugin.graph_api.streaming.workflow import (
    StreamingWorkflow,
    make_streaming_graph,
)


async def test_streaming_graph_api(client: Client) -> None:
    task_queue = f"streaming-test-{uuid.uuid4()}"
    plugin = LangGraphPlugin(
        graphs={"streaming": make_streaming_graph()},
        streaming_topic="tokens",
    )

    async with Worker(
        client,
        task_queue=task_queue,
        workflows=[StreamingWorkflow],
        plugins=[plugin],
    ):
        handle = await client.start_workflow(
            StreamingWorkflow.run,
            "a brave robot",
            id=f"streaming-{uuid.uuid4()}",
            task_queue=task_queue,
        )

        ws = WorkflowStreamClient.create(client, handle.id)
        tokens: list[dict[str, Any]] = []
        progress: list[dict[str, Any]] = []
        async for item in ws.subscribe(
            from_offset=0,
            result_type=dict,
            poll_cooldown=timedelta(milliseconds=10),
        ):
            if item.topic == "tokens":
                tokens.append(item.data)
            elif item.topic == "progress":
                if item.data.get("done"):
                    await handle.signal(StreamingWorkflow.ack_stream)
                    break
                progress.append(item.data)

        result = await handle.result()

    # Tokens reassemble into the final story.
    assert tokens, "expected at least one token"
    assert all("token" in t for t in tokens)
    assembled = "".join(t["token"] for t in tokens).strip()
    assert assembled == result

    # Workflow-side astream publish: one chunk per node, in order.
    assert [list(chunk)[0] for chunk in progress] == ["outline", "write_story"]
    assert result == progress[-1]["write_story"]["story"]
    assert "a brave robot" in result
