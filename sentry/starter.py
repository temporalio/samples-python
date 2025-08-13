import asyncio

from temporalio.client import Client
from temporalio.envconfig import ClientConfigProfile

from sentry.workflow import SentryExampleWorkflow, SentryExampleWorkflowInput


async def main():
    config_dict = ClientConfigProfile.load().to_dict()
    config_dict.setdefault("address", "localhost:7233")
    config = ClientConfigProfile.from_dict(config_dict)
    # Connect client
    client = await Client.connect(**config.to_client_connect_config())

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
