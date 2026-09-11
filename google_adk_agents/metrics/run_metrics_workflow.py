import asyncio

from temporalio.client import Client
from temporalio.contrib.google_adk_agents import GoogleAdkPlugin

from google_adk_agents.metrics.workflows.metrics_workflow import MetricsWorkflow


async def main() -> None:
    client = await Client.connect("localhost:7233", plugins=[GoogleAdkPlugin()])
    result = await client.execute_workflow(
        MetricsWorkflow.run,
        "Explain replay-safe metrics.",
        id="google-adk-agents-metrics-workflow-id",
        task_queue="google-adk-agents-metrics",
    )
    print(f"Result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
