import asyncio
import os
from pathlib import Path

from temporalio.client import Client
from temporalio.envconfig import ClientConfig

from sentry.workflow import SentryExampleWorkflow, SentryExampleWorkflowInput


async def main():
    config = ClientConfig.load_client_connect_config()
    config.setdefault("target_host", "localhost:7233")

    # Connect client
    client = await Client.connect(**config)

    # Run workflow
    try:
        result = await client.execute_workflow(
            SentryExampleWorkflow.run,
            SentryExampleWorkflowInput(option="broken"),
            id="sentry-workflow-id",
            task_queue="sentry-task-queue",
        )
        print(f"Workflow result: {result}")
    except Exception:
        print("Workflow failed - check Sentry for details")


if __name__ == "__main__":
    asyncio.run(main())
