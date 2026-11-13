"""Start the human in the loop workflow, wait for the request, approve it."""

# @@@SNIPSTART python-agent-framework-human-in-the-loop-run-workflow
import asyncio
import os

from temporalio.client import Client

from agent_framework_plugin.human_in_the_loop.workflow import (
    ApprovalRequest,
    HumanInTheLoopWorkflow,
)


async def main() -> None:
    client = await Client.connect(os.environ.get("TEMPORAL_ADDRESS", "localhost:7233"))

    handle = await client.start_workflow(
        HumanInTheLoopWorkflow.run,
        "Please delete /tmp/report.txt",
        id="agent-framework-human-in-the-loop",
        task_queue="agent-framework-human-in-the-loop",
    )

    # Poll the Query until the agent asks for approval.
    pending: list[ApprovalRequest] = []
    for _ in range(120):
        pending = await handle.query(HumanInTheLoopWorkflow.pending_approvals)
        if pending:
            break
        await asyncio.sleep(0.5)
    else:
        raise RuntimeError("the agent never asked for approval")

    for request in pending:
        print(f"Approval requested: {request.tool_name}({request.arguments})")

    # Send "reject" to see the agent handle a rejection.
    outcome = await handle.execute_update(HumanInTheLoopWorkflow.decide, "approve")
    print(f"Decision: {outcome}")

    result = await handle.result()
    print(f"Result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
# @@@SNIPEND
