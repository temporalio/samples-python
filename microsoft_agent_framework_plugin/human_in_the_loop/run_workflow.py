"""Start the human in the loop workflow, wait for the request, approve it."""

# @@@SNIPSTART python-microsoft-agent-framework-human-in-the-loop-run-workflow
import asyncio
import os

from temporalio.client import Client

from microsoft_agent_framework_plugin.human_in_the_loop.workflow import (
    ApprovalRequest,
    Decision,
    HumanInTheLoopWorkflow,
)


async def main() -> None:
    client = await Client.connect(os.environ.get("TEMPORAL_ADDRESS", "localhost:7233"))

    handle = await client.start_workflow(
        HumanInTheLoopWorkflow.run,
        "Please delete /tmp/report.txt",
        id="microsoft-agent-framework-human-in-the-loop",
        task_queue="microsoft-agent-framework-human-in-the-loop",
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
        # Set approved=False to see the rejection path.
        outcome = await handle.execute_update(
            HumanInTheLoopWorkflow.decide,
            Decision(request_id=request.request_id, approved=True),
        )
        print(f"Decision: {outcome}")

    result = await handle.result()
    print(f"Result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
# @@@SNIPEND
