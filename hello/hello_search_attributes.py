import asyncio

from temporalio import workflow
from temporalio.client import Client
from temporalio.worker import Worker
from temporalio.common import SearchAttributeKey

# define our custom search attribute to modify later in the workflow
custom_keyword_field = SearchAttributeKey.for_keyword("CustomKeywordField")


@workflow.defn
class GreetingWorkflow:
    @workflow.run
    async def run(self) -> None:
        # Wait a couple seconds, then alter the keyword search attribute
        await asyncio.sleep(2)
        workflow.upsert_search_attributes([
            custom_keyword_field.value_set("new-value")
        ])


async def main():
    # Start client
    client = await Client.connect("localhost:7233")

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
            search_attributes=custom_keyword_field.value_set("old-value"),
        )

        # Show search attributes before and after a few seconds
        print(
            "First search attribute values: ",
            (await handle.describe()).typed_search_attributes.get(custom_keyword_field),
        )
        await asyncio.sleep(3)
        print(
            "Second search attribute values: ",
            (await handle.describe()).typed_search_attributes.get(custom_keyword_field),
        )


if __name__ == "__main__":
    asyncio.run(main())
