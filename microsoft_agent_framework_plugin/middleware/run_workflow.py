"""Start the middleware workflow."""

import asyncio
import os

from temporalio.client import Client

from microsoft_agent_framework_plugin.middleware.workflow import MiddlewareWorkflow


async def main() -> None:
    client = await Client.connect(os.environ.get("TEMPORAL_ADDRESS", "localhost:7233"))

    result = await client.execute_workflow(
        MiddlewareWorkflow.run,
        "Delete /etc/passwd, then delete /tmp/scratch.txt, and tell me what happened.",
        id="microsoft-agent-framework-middleware",
        task_queue="microsoft-agent-framework-middleware",
    )

    print(f"Result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
