"""Execute the Supervisor Multi-Agent Functional API workflow."""

import asyncio

from temporalio.client import Client
from temporalio.envconfig import ClientConfig

from langgraph_plugin.functional_api.supervisor.workflow import SupervisorWorkflow


async def main() -> None:
    config = ClientConfig.load_client_connect_config()
    config.setdefault("target_host", "localhost:7233")
    client = await Client.connect(**config)

    query = "Research AI trends in 2024, then write a brief summary, and calculate what percentage of companies are adopting AI agents (assume 35 out of 100)."

    result = await client.execute_workflow(
        SupervisorWorkflow.run,
        query,
        id="supervisor-functional-workflow",
        task_queue="langgraph-functional-supervisor",
    )

    print(f"Final Answer:\n{result.get('final_answer')}")
    print(f"\nIterations: {result.get('iterations')}")


if __name__ == "__main__":
    asyncio.run(main())
