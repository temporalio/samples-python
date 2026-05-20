"""Start the hook-based HITL workflow and send an approval signal."""

import asyncio
import os

from temporalio.client import Client

from strands_plugin.human_in_the_loop.workflow import HumanInTheLoopWorkflow


async def main() -> None:
    client = await Client.connect(os.environ.get("TEMPORAL_ADDRESS", "localhost:7233"))

    handle = await client.start_workflow(
        HumanInTheLoopWorkflow.run,
        "Please delete /tmp/sensitive.txt",
        id="strands-human-in-the-loop",
        task_queue="strands-human-in-the-loop",
    )

    # Poll until the agent reaches the approval interrupt.
    reason = None
    while reason is None:
        await asyncio.sleep(0.5)
        reason = await handle.query(HumanInTheLoopWorkflow.pending_approval)
    print(f"Approval requested: {reason}")

    await handle.signal(HumanInTheLoopWorkflow.approve, "approve")

    result = await handle.result()
    print(f"Result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
