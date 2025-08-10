"""
Test app to compare both MCP integration approaches:
1. Minimal client (avoids anyio)
2. Standard MCP ClientSession with Nexus transport (experimental)
"""

import asyncio
import sys
import uuid

from temporalio.client import Client

from mcp_sequential_thinking.agent_workflow import AgentWorkflow
from mcp_sequential_thinking.agent_workflow_with_transport import (
    AgentWorkflowWithTransport,
)


async def main():
    # Check command line argument
    use_transport = len(sys.argv) > 1 and sys.argv[1] == "--transport"

    client = await Client.connect("localhost:7233")

    # Choose workflow class based on flag
    if use_transport:
        print("Using experimental MCP ClientSession with Nexus transport...")
        workflow_class = AgentWorkflowWithTransport
        workflow_id = f"mcp-transport-test-{uuid.uuid4().hex[:8]}"
    else:
        print("Using minimal MCP client...")
        workflow_class = AgentWorkflow
        workflow_id = f"mcp-minimal-test-{uuid.uuid4().hex[:8]}"

    # Start the workflow
    handle = await client.start_workflow(
        workflow_class.run,
        id=workflow_id,
        task_queue="mcp-sequential-thinking-task-queue",
    )

    print(f"Started workflow {handle.id}")

    # Wait for completion
    try:
        result = await handle.result()
        print("\nWorkflow completed successfully!")
        print(f"Result: {result}")
    except Exception as e:
        print(f"\nWorkflow failed with error: {e}")
        raise


if __name__ == "__main__":
    print("\nMCP Integration Comparison")
    print("==========================")
    print("Usage:")
    print("  python app_compare.py           # Use minimal client (default)")
    print("  python app_compare.py --transport  # Use experimental ClientSession\n")

    asyncio.run(main())
