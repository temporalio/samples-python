"""Run the Approval Workflow worker.

Starts a Temporal worker that can execute the approval workflow.

Usage:
    python -m langgraph_samples.human_in_loop.approval_workflow.run_worker
"""

import asyncio
from datetime import timedelta

from temporalio.client import Client
from temporalio.contrib.langgraph import LangGraphPlugin
from temporalio.envconfig import ClientConfig
from temporalio.worker import Worker

from langgraph_samples.human_in_loop.approval_workflow.graph import build_approval_graph
from langgraph_samples.human_in_loop.approval_workflow.workflow import ApprovalWorkflow

TASK_QUEUE = "langgraph-approval"


async def main() -> None:
    # Create the LangGraph plugin with the approval graph
    plugin = LangGraphPlugin(
        graphs={"approval_workflow": build_approval_graph},
        default_activity_timeout=timedelta(seconds=30),
    )

    # Connect to Temporal
    config = ClientConfig.load_client_connect_config()
    config.setdefault("target_host", "localhost:7233")
    client = await Client.connect(**config, plugins=[plugin])

    # Create and run worker
    worker = Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=[ApprovalWorkflow],
        # Activities are registered by the plugin
    )

    print(f"Starting approval workflow worker on task queue: {TASK_QUEUE}")
    print("Press Ctrl+C to stop")

    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
