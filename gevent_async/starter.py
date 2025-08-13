# Init gevent
from gevent import monkey

monkey.patch_all()

import asyncio
import logging

from temporalio.client import Client
from temporalio.envconfig import ClientConfigProfile

from gevent_async import workflow
from gevent_async.executor import GeventExecutor


def main():
    logging.basicConfig(level=logging.INFO)

    # Create single-worker gevent executor and run asyncio.run(async_main()) in
    # it, waiting for result. This executor cannot be used for anything else in
    # Temporal, it is just a single thread for running asyncio.
    with GeventExecutor(max_workers=1) as executor:
        executor.submit(asyncio.run, async_main()).result()


async def async_main():
    # Connect client
    config_dict = ClientConfigProfile.load().to_dict()
    config_dict.setdefault("address", "localhost:7233")
    config = ClientConfigProfile.from_dict(config_dict)
    client = await Client.connect(**config.to_client_connect_config())

    # Run workflow
    result = await client.execute_workflow(
        workflow.GreetingWorkflow.run,
        "Temporal",
        id="gevent_async-workflow-id",
        task_queue="gevent_async-task-queue",
    )
    logging.info(f"Workflow result: {result}")


if __name__ == "__main__":
    main()
