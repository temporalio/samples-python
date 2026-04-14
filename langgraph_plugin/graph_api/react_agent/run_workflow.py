"""Start the ReAct agent workflow (Graph API)."""

import asyncio

from temporalio.client import Client

from langgraph_plugin.graph_api.react_agent.workflow import ReactAgentWorkflow


async def main() -> None:
    client = await Client.connect("localhost:7233")

    result = await client.execute_workflow(
        ReactAgentWorkflow.run,
        "Tell me about San Francisco",
        id="react-agent-workflow",
        task_queue="langgraph-react-agent",
    )

    print(f"Agent answer: {result}")


if __name__ == "__main__":
    asyncio.run(main())
