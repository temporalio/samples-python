"""Test anyio in Temporal workflow"""

import asyncio
import json
import uuid

from temporalio.client import Client

from mcp_sequential_thinking.test_anyio_workflow import TestAnyioWorkflow


async def main():
    client = await Client.connect("localhost:7233")

    # Start the test workflow
    handle = await client.start_workflow(
        TestAnyioWorkflow.run,
        id=f"test-anyio-{uuid.uuid4().hex[:8]}",
        task_queue="mcp-sequential-thinking-task-queue",
    )

    print("Started anyio test workflow...")

    # Wait for result
    result = await handle.result()

    print("\nAnyio Test Results:")
    print("=" * 50)
    print(json.dumps(result, indent=2))

    if result["success"]:
        print("\n✅ anyio works in Temporal workflows!")
    else:
        print(f"\n❌ anyio failed: {result['error']}")


if __name__ == "__main__":
    asyncio.run(main())
