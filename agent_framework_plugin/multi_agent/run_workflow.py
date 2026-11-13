"""Start the multi-agent workflow."""

import asyncio
import os

from temporalio.client import Client

from agent_framework_plugin.multi_agent.workflow import MultiAgentWorkflow


async def main() -> None:
    client = await Client.connect(os.environ.get("TEMPORAL_ADDRESS", "localhost:7233"))

    result = await client.execute_workflow(
        MultiAgentWorkflow.run,
        "durable execution",
        id="agent-framework-multi-agent",
        task_queue="agent-framework-multi-agent",
    )

    print(f"Result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
