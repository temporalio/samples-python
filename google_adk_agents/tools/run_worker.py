from __future__ import annotations

import asyncio

from temporalio.client import Client
from temporalio.contrib.google_adk_agents import GoogleAdkPlugin
from temporalio.worker import Worker

from google_adk_agents.tools.activities.weather_activity import get_weather
from google_adk_agents.tools.workflows.weather_workflow import WeatherAgentWorkflow


async def main():
    # Build the plugin once and give the same instance to the client and the
    # worker.
    plugin = GoogleAdkPlugin()

    client = await Client.connect("localhost:7233", plugins=[plugin])

    worker = Worker(
        client,
        task_queue="google-adk-agents-tools",
        workflows=[WeatherAgentWorkflow],
        activities=[get_weather],
        plugins=[plugin],
    )
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
