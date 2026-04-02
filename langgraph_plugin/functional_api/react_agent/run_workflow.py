"""Execute the ReAct Agent Functional API workflow.

Connects to Temporal and starts the ReActAgentWorkflow.
"""

import asyncio

from temporalio.client import Client
from temporalio.envconfig import ClientConfig

from langgraph_plugin.functional_api.react_agent.workflow import ReActAgentWorkflow


async def main() -> None:
    config = ClientConfig.load_client_connect_config()
    config.setdefault("target_host", "localhost:7233")
    client = await Client.connect(**config)

    query = "What's the weather in New York? Then calculate: if it's 72°F, what is that in Celsius? Use the formula (F-32)*5/9"

    # Execute the workflow
    result = await client.execute_workflow(
        ReActAgentWorkflow.run,
        query,
        id="react-agent-functional-workflow",
        task_queue="langgraph-functional-react-agent",
    )

    print(f"Final Answer: {result.get('final_answer')}")
    print(f"Iterations: {result.get('iterations')}")


if __name__ == "__main__":
    asyncio.run(main())
