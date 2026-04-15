"""Start the ReAct agent workflow (Functional API)."""

import asyncio
import os

from temporalio.client import Client

from langgraph_plugin.functional_api.react_agent.workflow import (
    ReactAgentFunctionalWorkflow,
)


async def main() -> None:
    client = await Client.connect(os.environ.get("TEMPORAL_ADDRESS", "localhost:7233"))

    result = await client.execute_workflow(
        ReactAgentFunctionalWorkflow.run,
        "Tell me about San Francisco",
        id="react-agent-functional-workflow",
        task_queue="langgraph-react-agent-functional",
    )

    print(f"Agent answer: {result['answer']}")
    print(f"Tool calls made: {result['steps']}")


if __name__ == "__main__":
    asyncio.run(main())
