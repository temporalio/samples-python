import asyncio

from temporalio.client import Client
from temporalio.contrib.google_adk_agents import GoogleAdkPlugin

from google_adk_agents.tools.workflows.weather_workflow import WeatherAgentWorkflow


async def main():
    client = await Client.connect("localhost:7233", plugins=[GoogleAdkPlugin()])

    result = await client.execute_workflow(
        WeatherAgentWorkflow.run,
        "What is the weather in New York?",
        id="google-adk-agents-tools-workflow-id",
        task_queue="google-adk-agents-tools",
    )
    print(f"Result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
