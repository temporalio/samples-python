"""Execute the Reflection Agent Functional API workflow.

Connects to Temporal and starts the ReflectionWorkflow.
"""

import asyncio

from temporalio.client import Client
from temporalio.envconfig import ClientConfig

from langgraph_plugin.functional_api.reflection.workflow import ReflectionWorkflow


async def main() -> None:
    config = ClientConfig.load_client_connect_config()
    config.setdefault("target_host", "localhost:7233")
    client = await Client.connect(**config)

    task = "Write a short paragraph explaining the benefits of using Temporal for AI agent workflows."

    result = await client.execute_workflow(
        ReflectionWorkflow.run,
        task,
        id="reflection-functional-workflow",
        task_queue="langgraph-functional-reflection",
    )

    print(f"Status: {result.get('status')}")
    print(f"Iterations: {result.get('iterations')}")
    print(f"Final Score: {result.get('final_score')}/10")
    print(f"\nFinal Content:\n{result.get('final_content')}")


if __name__ == "__main__":
    asyncio.run(main())
