import asyncio
import os
import sys
import uuid

from temporalio.client import Client
from temporalio.envconfig import ClientConfig

from litellm_activity.shared import DEFAULT_MODEL, TASK_QUEUE, LLMRequest
from litellm_activity.workflow import LiteLLMWorkflow


async def main() -> None:
    config = ClientConfig.load_client_connect_config()
    config.setdefault("target_host", "localhost:7233")
    client = await Client.connect(**config)

    prompt = " ".join(sys.argv[1:]) or "Explain Temporal in one sentence."
    request = LLMRequest(
        prompt=prompt,
        model=os.getenv("LITELLM_MODEL", DEFAULT_MODEL),
    )
    result = await client.execute_workflow(
        LiteLLMWorkflow.run,
        request,
        id=f"litellm-activity-{uuid.uuid4()}",
        task_queue=TASK_QUEUE,
    )
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
