import asyncio

from temporalio import workflow
from temporalio.client import Client
from temporalio.worker import Worker


@workflow.defn
class GreetingWorkflow:
    @workflow.run
    async def run(self) -> None:
        # Wait a couple seconds, then alter the keyword search attribute
        await asyncio.sleep(2)
        workflow.upsert_search_attributes({"CustomKeywordField": ["new-value"]})


async def main():
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
        task_queue="hello-search-attributes-task-queue",
        workflows=[GreetingWorkflow],
    ):

        # While the worker is running, use the client to start the workflow.
        # Note, in many production setups, the client would be in a completely
        # separate process from the worker.
        handle = await client.start_workflow(
            GreetingWorkflow.run,
            id="hello-search-attributes-workflow-id",
            task_queue="hello-search-attributes-task-queue",
            # Start with default set of search attributes
            search_attributes={"CustomKeywordField": ["old-value"]},
        )

        # Show search attributes before and after a few seconds
        print(
            "First search attribute values: ",
            (await handle.describe()).search_attributes.get("CustomKeywordField"),
        )
        await asyncio.sleep(3)
        print(
            "Second search attribute values: ",
            (await handle.describe()).search_attributes.get("CustomKeywordField"),
        )


if __name__ == "__main__":
    asyncio.run(main())
