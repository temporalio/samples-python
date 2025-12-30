"""Run the Approval Workflow worker (Condition-based).

Starts a Temporal worker that can execute the approval workflow.
"""

import asyncio
from datetime import timedelta

from temporalio.client import Client
from temporalio.contrib.langgraph import LangGraphPlugin
from temporalio.envconfig import ClientConfig
from temporalio.worker import Worker

from langgraph_samples.human_in_the_loop.approval_workflow_condition.graph import (
    build_approval_graph,
    notify_approver,
)
from langgraph_samples.human_in_the_loop.approval_workflow_condition.workflow import ApprovalWorkflow

TASK_QUEUE = "langgraph-approval-condition"


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
        activities=[notify_approver],
    )

    print(f"Starting approval workflow worker on task queue: {TASK_QUEUE}")
    print("Press Ctrl+C to stop")

    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
