"""Test the debug workflow to inspect Temporal's event loop"""

import asyncio
import json

from temporalio.client import Client

from mcp_sequential_thinking.debug_workflow import DebugEventLoopWorkflow


async def main():
    client = await Client.connect("localhost:7233")

    import uuid

    # Start the debug workflow
    handle = await client.start_workflow(
        DebugEventLoopWorkflow.run,
        id=f"debug-event-loop-test-{uuid.uuid4().hex[:8]}",
        task_queue="mcp-sequential-thinking-task-queue",
    )

    print("Started debug workflow...")

    # Wait for result
    result = await handle.result()

    print("\nEvent Loop Debug Info:")
    print("=" * 50)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
