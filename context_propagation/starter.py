import asyncio
import logging
from pathlib import Path

from temporalio.client import Client
from temporalio.envconfig import ClientConfig

from context_propagation import interceptor, shared, workflows


async def main():
    logging.basicConfig(level=logging.INFO)

    # Set the user ID
    shared.user_id.set("some-user")

    # Get repo root - 1 level deep from root


    repo_root = Path(__file__).resolve().parent.parent


    config_file = repo_root / "temporal.toml"


    
    config = ClientConfig.load_client_connect_config(config_file=str(config_file))
    config["target_host"] = "localhost:7233"
    # Use our interceptor
    config["interceptors"] = [interceptor.ContextPropagationInterceptor()]
    
    # Connect client
    client = await Client.connect(**config)

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
