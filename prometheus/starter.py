import asyncio

from temporalio.client import Client

from prometheus.worker import GreetingWorkflow, init_runtime_with_prometheus

interrupt_event = asyncio.Event()


async def main():
    runtime = init_runtime_with_prometheus(9001)

    # Connect client
    client = await Client.connect(
        "localhost:7233",
        runtime=runtime,
    )

    # Run workflow
    result = await client.execute_workflow(
        GreetingWorkflow.run,
        "Temporal",
        id="prometheus-workflow-id",
        task_queue="prometheus-task-queue",
    )
    print(f"Workflow result: {result}")
    print(
        "Prometheus client metrics available at http://127.0.0.1:9001/metrics, ctrl+c to exit"
    )
    await interrupt_event.wait()


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        interrupt_event.set()
        loop.run_until_complete(loop.shutdown_asyncgens())
