import asyncio
import logging

from temporalio.client import Client
from temporalio.envconfig import ClientConfig

from context_propagation import interceptor, shared, workflows
from util import get_temporal_config_path


async def main():
    logging.basicConfig(level=logging.INFO)

    # Set the user ID
    shared.user_id.set("some-user")

    config = ClientConfig.load_client_connect_config()
    config.setdefault("target_host", "localhost:7233")

    # Connect client
    client = await Client.connect(
        **config,
        # Use our interceptor
        interceptors=[interceptor.ContextPropagationInterceptor()],
    )

    # Start workflow, send signal, wait for completion, issue query
    handle = await client.start_workflow(
        workflows.SayHelloWorkflow.run,
        "Temporal",
        id=f"context-propagation-workflow-id",
        task_queue="context-propagation-task-queue",
    )
    await handle.signal(workflows.SayHelloWorkflow.signal_complete)
    result = await handle.result()
    logging.info(f"Workflow result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
