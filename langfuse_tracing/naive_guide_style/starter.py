"""ANTI-PATTERN starter — see workflow.py and README.md."""

import asyncio
import uuid

from temporalio.client import Client
from temporalio.envconfig import ClientConfig

from langfuse_tracing.naive_guide_style.workflow import NaiveGuideStyleWorkflow

TASK_QUEUE = "langfuse-naive-guide-style-task-queue"


async def main() -> None:
    config = ClientConfig.load_client_connect_config()
    config.setdefault("target_host", "localhost:7233")
    client = await Client.connect(**config)

    workflow_id = f"naive-guide-style-{uuid.uuid4().hex[:8]}"
    result = await client.execute_workflow(
        NaiveGuideStyleWorkflow.run,
        "durable execution",
        id=workflow_id,
        task_queue=TASK_QUEUE,
    )
    print(f"Workflow {workflow_id} result:\n{result}")
    print(
        "Now look at Langfuse: one workflow produced several disconnected traces "
        "with duplicated agent spans. Compare with the ticket_triage sample."
    )


if __name__ == "__main__":
    asyncio.run(main())
