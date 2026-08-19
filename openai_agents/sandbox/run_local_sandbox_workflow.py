from __future__ import annotations

import asyncio

from temporalio.client import Client
from temporalio.contrib.openai_agents import OpenAIAgentsPlugin

from openai_agents.sandbox.shared import TASK_QUEUE
from openai_agents.sandbox.workflows.local_sandbox_workflow import (
    LocalSandboxWorkflow,
)


async def main() -> None:
    client = await Client.connect(
        "localhost:7233",
        plugins=[OpenAIAgentsPlugin()],
    )

    result = await client.execute_workflow(
        LocalSandboxWorkflow.run,
        "Write a file holding the first 20 Fibonacci numbers, one per line, "
        "then tell me how many lines it has and what the last one is.",
        id="openai-agents-sandbox",
        task_queue=TASK_QUEUE,
    )
    print(f"Result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
