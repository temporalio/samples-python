"""Execute the ReAct Agent workflow.

Usage:
    # First, in another terminal, start the worker:
    python -m langgraph_samples.basic.react_agent.run_worker

    # Then run this script:
    python -m langgraph_samples.basic.react_agent.run_workflow
"""

import asyncio

from temporalio.client import Client
from temporalio.envconfig import ClientConfig

from langgraph_samples.basic.react_agent.workflow import ReActAgentWorkflow


async def main() -> None:
    config = ClientConfig.load_client_connect_config()
    config.setdefault("target_host", "localhost:7233")
    client = await Client.connect(**config)

    result = await client.execute_workflow(
        ReActAgentWorkflow.run,
        "What's the weather like in Tokyo?",
        id="react-agent-workflow",
        task_queue="langgraph-react-agent",
    )

    # Print only the text response
    print(result["messages"][-1]["content"])


if __name__ == "__main__":
    asyncio.run(main())
