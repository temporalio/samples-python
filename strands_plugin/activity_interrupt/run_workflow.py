"""Start the activity interrupt workflow."""

import asyncio
import os

from temporalio.client import Client
from temporalio.contrib.strands import StrandsPlugin

from strands_plugin.activity_interrupt.workflow import ActivityInterruptWorkflow


async def main() -> None:
    # The starter also goes through the plugin's failure converter so the
    # Interrupt payload deserializes cleanly when the workflow result is read.
    client = await Client.connect(
        os.environ.get("TEMPORAL_ADDRESS", "localhost:7233"),
        plugins=[StrandsPlugin()],
    )

    handle = await client.start_workflow(
        ActivityInterruptWorkflow.run,
        "Please delete the 'system' user.",
        id="strands-activity-interrupt",
        task_queue="strands-activity-interrupt",
    )

    reason = None
    while reason is None:
        await asyncio.sleep(0.5)
        reason = await handle.query(ActivityInterruptWorkflow.pending_approval)
    print(f"Approval requested: {reason}")

    await handle.signal(ActivityInterruptWorkflow.approve, "approve")

    result = await handle.result()
    print(f"Result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
