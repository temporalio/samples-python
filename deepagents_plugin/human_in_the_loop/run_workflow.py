"""Start the HITL workflow, wait for the approval prompt, then approve it.

Starts the agent, polls the ``pending_approval`` query until the agent pauses on
the guarded ``book_trip`` tool, then sends the ``resume`` update with a decision.
In a real app the query result would be shown to a person and the update sent
from a UI.
"""

import asyncio
import os

from temporalio.client import Client

from deepagents_plugin.human_in_the_loop.workflow import HumanInTheLoopAgent


async def main() -> None:
    client = await Client.connect(os.environ.get("TEMPORAL_ADDRESS", "localhost:7233"))

    handle = await client.start_workflow(
        HumanInTheLoopAgent.run,
        "Rome",
        id="deepagents-human-in-the-loop",
        task_queue="deepagents-human-in-the-loop",
    )

    # Poll the query until the agent surfaces the pending approval.
    for _ in range(100):
        pending = await handle.query(HumanInTheLoopAgent.pending_approval)
        if pending is not None:
            print(f"Approval requested: {pending}")
            break
        await asyncio.sleep(0.5)
    else:
        raise RuntimeError("workflow never surfaced an approval prompt")

    print("Approving...")
    await handle.execute_update(HumanInTheLoopAgent.resume, "approve")

    result = await handle.result()
    print(f"Result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
