import asyncio

from temporalio.client import Client

from workflows.basic_model_workflow import BasicModelWorkflow


async def main():
    # Create client connected to server at the given address
    client = await Client.connect(
        "localhost:7233",
    )

    # Execute a workflow
    result = await client.execute_workflow(
        BasicModelWorkflow.run,
        args=["How do I check if a Python object is an instance of a class?"],
        id="basic-model-workflow",
        task_queue="openai-basic-task-queue",
    )

    print(f"Result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
