"""Start the control flow pipeline workflow (Functional API)."""

import asyncio
import os

from temporalio.client import Client

from langgraph_plugin.functional_api.control_flow.workflow import (
    ControlFlowWorkflow,
)


async def main() -> None:
    client = await Client.connect(os.environ.get("TEMPORAL_ADDRESS", "localhost:7233"))

    items = [
        "Fix login bug",
        "URGENT: Production outage in payments",
        "Update README",
        "INVALID:",
        "Urgent: Security patch needed",
        "Refactor test suite",
    ]

    result = await client.execute_workflow(
        ControlFlowWorkflow.run,
        items,
        id="control-flow-workflow",
        task_queue="langgraph-control-flow",
    )

    print(f"Summary: {result['summary']}")
    for r in result["results"]:
        print(f"  {r}")


if __name__ == "__main__":
    asyncio.run(main())
