import asyncio

from temporalio.client import Client

from multiline_logging.workflows import MultilineLoggingWorkflow


async def main():
    client = await Client.connect("localhost:7233")

    test_cases = [
        "activity_exception",
        "complex_activity_exception",
        "workflow_exception",
    ]

    for test_case in test_cases:
        print(f"\n--- Testing {test_case} ---")
        try:
            result = await client.execute_workflow(
                MultilineLoggingWorkflow.run,
                test_case,
                id=f"multiline-logging-{test_case}",
                task_queue="multiline-logging-task-queue",
            )
            print(f"Result: {result}")
        except Exception as e:
            print(f"Expected exception caught: {e}")


if __name__ == "__main__":
    asyncio.run(main())
