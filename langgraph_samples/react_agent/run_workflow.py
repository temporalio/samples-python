"""Execute the ReAct Agent workflow."""

import asyncio

from temporalio.client import Client
from temporalio.envconfig import ClientConfig

from langgraph_samples.react_agent.workflow import ReActAgentWorkflow


async def main() -> None:
    config = ClientConfig.load_client_connect_config()
    config.setdefault("target_host", "localhost:7233")
    client = await Client.connect(**config)

    # This query requires multiple tool calls:
    # 1. First, get_weather to find the temperature in Tokyo
    # 2. Then, calculate to convert Fahrenheit to Celsius
    result = await client.execute_workflow(
        ReActAgentWorkflow.run,
        "What's the weather in Tokyo? Convert the temperature to Celsius.",
        id="react-agent-workflow",
        task_queue="langgraph-react-agent",
    )

    # Print only the text response
    print(result["messages"][-1]["content"])


if __name__ == "__main__":
    asyncio.run(main())
