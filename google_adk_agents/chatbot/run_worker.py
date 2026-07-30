from __future__ import annotations

import asyncio
import os

from temporalio.client import Client
from temporalio.contrib.google_adk_agents import GoogleAdkPlugin
from temporalio.worker import Worker

from google_adk_agents.chatbot.workflows.chatbot_workflow import (
    ChatbotAgentWorkflow,
)


async def main():
    # @@@SNIPSTART google-adk-agents-chatbot-worker
    plugin = GoogleAdkPlugin()

    client = await Client.connect(
        os.environ.get("TEMPORAL_ADDRESS", "localhost:7233"), plugins=[plugin]
    )

    worker = Worker(
        client,
        task_queue="google-adk-agents-chatbot",
        workflows=[ChatbotAgentWorkflow],
        plugins=[plugin],
    )
    await worker.run()
    # @@@SNIPEND


if __name__ == "__main__":
    asyncio.run(main())
