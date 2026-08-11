"""Run the LangSmith tracing Deep Agents sample.

Single-process driver: starts a Worker, executes the Workflow once, prints the
result, then shuts down. Composes ``LangSmithPlugin`` with ``DeepAgentsPlugin``
so the agent runs durably *and* its LLM calls are traced to LangSmith.
Registration order of the two plugins does not matter.

Requires ``ANTHROPIC_API_KEY`` and ``LANGSMITH_API_KEY`` (or ``LANGCHAIN_API_KEY``)
in the environment.
"""

import asyncio
import os

from temporalio.client import Client
from temporalio.contrib.deepagents import DeepAgentsPlugin
from temporalio.contrib.langsmith import LangSmithPlugin
from temporalio.worker import Worker

from deepagents_plugin.langsmith_tracing.workflow import TracedAgent


async def main() -> None:
    client = await Client.connect(
        os.environ.get("TEMPORAL_ADDRESS", "localhost:7233"),
        plugins=[
            # Register observability first, then the Deep Agents plugin.
            LangSmithPlugin(),
            DeepAgentsPlugin(),
        ],
    )

    async with Worker(
        client,
        task_queue="deepagents-langsmith-tracing",
        workflows=[TracedAgent],
    ):
        result = await client.execute_workflow(
            TracedAgent.run,
            "What is durable execution, in one sentence?",
            id="deepagents-langsmith-tracing",
            task_queue="deepagents-langsmith-tracing",
        )
        print(f"Result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
