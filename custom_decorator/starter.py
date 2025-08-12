import asyncio

from temporalio.client import Client
from temporalio.envconfig import ClientConfig

from custom_decorator.worker import WaitForCancelWorkflow
from util import get_temporal_config_path


async def main():
    # Connect client
    config = ClientConfig.load_client_connect_config()
    config.setdefault("target_host", "localhost:7233")
    client = await Client.connect(**config)

    # Start the workflow
    handle = await client.start_workflow(
        WaitForCancelWorkflow.run,
        id=f"custom_decorator-workflow-id",
        task_queue="custom_decorator-task-queue",
    )
    print("Started workflow, waiting 5 seconds before cancelling")
    await asyncio.sleep(5)

    # Send a signal asking workflow to cancel the activity
    await handle.signal(WaitForCancelWorkflow.cancel_activity)

    # Wait and expect to be told about the activity being cancelled. If we did
    # not have the automatic heartbeater decorator, the signal would have failed
    # because the workflow would already be completed as failed with activity
    # heartbeat timeout.
    result = await handle.result()
    print(f"Result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
