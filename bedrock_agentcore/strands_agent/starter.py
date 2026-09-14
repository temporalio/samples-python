import asyncio
import sys

from strands.models import BedrockModel
from temporalio.client import Client
from temporalio.contrib.strands import StrandsPlugin
from temporalio.envconfig import ClientConfig

from workflows import MODEL_ID, MODEL_NAME, TASK_QUEUE, StrandsAgentWorkflow

DEFAULT_PROMPT = (
    "What is the 30th Fibonacci number, and is it divisible by 7? "
    "Verify your answer by running code."
)


async def main() -> None:
    prompt = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_PROMPT

    # Reads TEMPORAL_ADDRESS / TEMPORAL_NAMESPACE / TEMPORAL_API_KEY -- the same
    # variables the Worker gets from agentcore/agentcore.json. TLS is enabled
    # automatically alongside an API key.
    config = ClientConfig.load_client_connect_config()
    config.setdefault("target_host", "localhost:7233")
    client = await Client.connect(
        **config,
        plugins=[
            StrandsPlugin(models={MODEL_NAME: lambda: BedrockModel(model_id=MODEL_ID)})
        ],
    )
    print("Connected to Temporal Service")

    result = await client.execute_workflow(
        StrandsAgentWorkflow.run,
        prompt,
        id="agentcore-strands-workflow-id-1",
        task_queue=TASK_QUEUE,
    )
    print(f"Agent result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
