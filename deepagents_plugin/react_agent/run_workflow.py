"""Start the react agent workflow and print the final answer."""

import asyncio
import os

from temporalio.client import Client

from deepagents_plugin.react_agent.workflow import ReactAgent


async def main() -> None:
    client = await Client.connect(os.environ.get("TEMPORAL_ADDRESS", "localhost:7233"))

    result = await client.execute_workflow(
        ReactAgent.run,
        "What's the weather in Seattle, and what is Temporal known for?",
        id="deepagents-react-agent",
        task_queue="deepagents-react-agent",
    )

    print(f"Result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
