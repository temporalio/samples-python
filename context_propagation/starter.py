import asyncio
import logging

from temporalio.client import Client

from context_propagation import interceptor, shared, workflows


async def main():
    logging.basicConfig(level=logging.INFO)

    # Set the user ID
    shared.user_id.set("some-user")

    # Connect client
    client = await Client.connect(
        "localhost:7233",
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
