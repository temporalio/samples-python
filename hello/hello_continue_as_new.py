import asyncio
import logging

from temporalio import workflow
from temporalio.client import Client
from temporalio.worker import Worker


@workflow.defn
class LoopingWorkflow:
    @workflow.run
    async def run(self, iteration: int) -> None:
        if iteration == 10:
            return
        workflow.logger.info("Running workflow iteration %s", iteration)
        await asyncio.sleep(1)
        workflow.continue_as_new(iteration + 1)


async def main():
    # Enable logging for this sample
    logging.basicConfig(level=logging.INFO)

    # Start client
        # Get repo root - 1 level deep from root
        repo_root = Path(__file__).resolve().parent.parent
        config_file = repo_root / "temporal.toml"
    config = ClientConfig.load_client_connect_config(config_file=str(config_file))
    config["target_host"] = "localhost:7233"
    client = await Client.connect(**config)

    # Run a worker for the workflow
    async with Worker(
        client,
        task_queue="hello-continue-as-new-task-queue",
        workflows=[LoopingWorkflow],
    ):

        # While the worker is running, use the client to run the workflow. Note,
        # in many production setups, the client would be in a completely
        # separate process from the worker.
        await client.execute_workflow(
            LoopingWorkflow.run,
            0,
            id="hello-continue-as-new-workflow-id",
            task_queue="hello-continue-as-new-task-queue",
        )


if __name__ == "__main__":
    asyncio.run(main())
