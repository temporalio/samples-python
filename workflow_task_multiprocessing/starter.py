import asyncio
import argparse
import uuid

from temporalio.client import Client
from temporalio.envconfig import ClientConfig

from workflow_task_multiprocessing import WORKFLOW_TASK_QUEUE
from workflow_task_multiprocessing.workflows import ParallelizedWorkflow


class Args(argparse.Namespace):
    num_workflows: int


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-n",
        "--num-workflows",
        help="the number of workflows to execute",
        type=int,
        default=25,
    )
    args = parser.parse_args(namespace=Args())

    config = ClientConfig.load_client_connect_config()
    config.setdefault("target_host", "localhost:7233")
    client = await Client.connect(**config)

    # Start several workflows
    wf_handles = [
        client.execute_workflow(
            ParallelizedWorkflow.run,
            "temporal",
            id=f"greeting-workflow-id-{uuid.uuid4()}",
            task_queue=WORKFLOW_TASK_QUEUE,
        )
        for _ in range(args.num_workflows)
    ]

    # Wait for workflow completion (runs indefinitely until it receives a signal)
    for wf in asyncio.as_completed(wf_handles):
        result = await wf
        print(result)


if __name__ == "__main__":
    asyncio.run(main())
