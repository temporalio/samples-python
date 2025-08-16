"""Run the agent workflow with LLM to solve problems using sequential thinking."""

import asyncio
import sys
import uuid
from temporalio.client import Client

from mcp_examples.sequential_thinking.agent_workflow_with_llm import (
    AgentWorkflowWithLLM,
)


async def main():
    """Run the agent workflow with a problem to solve."""

    # Get problem from command line or use default
    if len(sys.argv) > 1:
        problem = " ".join(sys.argv[1:])
    else:
        # Default problem examples
        problem = (
            "What is the optimal strategy for implementing a distributed cache system?"
        )

    print(f"Problem: {problem}")
    print("=" * 80)

    # Connect to Temporal
    client = await Client.connect("localhost:7233")

    # Start the workflow
    workflow_id = f"agent-llm-{uuid.uuid4().hex[:8]}"
    handle = await client.start_workflow(
        AgentWorkflowWithLLM.run,
        problem,
        id=workflow_id,
        task_queue="mcp-sequential-thinking-task-queue",
    )

    print(f"Started workflow {handle.id}")
    print("Thinking...\n")

    try:
        # Wait for the result
        result = await handle.result()
        print(result)
    except Exception as e:
        print(f"\nWorkflow failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
