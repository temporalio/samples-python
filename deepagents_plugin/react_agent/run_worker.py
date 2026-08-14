"""Worker for the react agent sample.

The plugin registers the ``deepagents.*`` activities automatically, but the
user's own ``get_weather`` activity (exposed to the agent via
``activity_as_tool``) must be registered on the worker like any other activity.
The ``web_search`` tool wrapped with ``tool_as_activity`` needs no separate
registration — it runs through the plugin's ``deepagents.invoke_tool`` activity.
"""

import asyncio
import os

from temporalio.client import Client
from temporalio.contrib.deepagents import DeepAgentsPlugin
from temporalio.worker import Worker

from deepagents_plugin.react_agent.workflow import ReactAgent, get_weather


async def main() -> None:
    client = await Client.connect(
        os.environ.get("TEMPORAL_ADDRESS", "localhost:7233"),
        plugins=[DeepAgentsPlugin()],
    )

    worker = Worker(
        client,
        task_queue="deepagents-react-agent",
        workflows=[ReactAgent],
        activities=[get_weather],
    )
    print("Worker started. Ctrl+C to exit.")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
