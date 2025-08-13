import asyncio

from temporalio.client import Client
from temporalio.envconfig import ClientConfigProfile
from temporalio.worker import Worker

from custom_converter.shared import greeting_data_converter
from custom_converter.workflow import GreetingWorkflow

interrupt_event = asyncio.Event()


async def main():
    config = ClientConfigProfile.load()
    config["address"] = "localhost:7233"

    # Connect client
    client = await Client.connect(
        **config.to_client_connect_config(),
        # Without this, when trying to run a workflow, we get:
        #   KeyError: 'Unknown payload encoding my-greeting-encoding
        data_converter=greeting_data_converter,
    )

    # Run a worker for the workflow
    async with Worker(
        client,
        task_queue="custom_converter-task-queue",
        workflows=[GreetingWorkflow],
    ):
        # Wait until interrupted
        print("Worker started, ctrl+c to exit")
        await interrupt_event.wait()
        print("Shutting down")


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        interrupt_event.set()
        loop.run_until_complete(loop.shutdown_asyncgens())
