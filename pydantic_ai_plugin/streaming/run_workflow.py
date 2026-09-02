import asyncio
import uuid

from temporalio.client import Client

from pydantic_ai.durable_exec.temporal import PydanticAIPlugin
from pydantic_ai_plugin.streaming.workflow import (
    StreamingInput,
    StreamingWorkflow,
    durability,
)


async def main() -> None:
    client = await Client.connect(
        "localhost:7233",
        plugins=[PydanticAIPlugin()],
    )
    handle = await client.start_workflow(
        StreamingWorkflow.run,
        StreamingInput(prompt="Explain durable execution in one sentence."),
        id=f"pydantic-ai-streaming-{uuid.uuid4()}",
        task_queue="pydantic-ai-streaming",
    )
    events = durability.stream_agent_events(client, handle, output_type=str)
    async for event in events:
        print(type(event).__name__, event)
    print(await handle.result())


if __name__ == "__main__":
    asyncio.run(main())
