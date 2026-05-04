"""Run the LangSmith tracing chat sample (Functional API).

Single-process driver: starts a Worker, executes the Workflow once, prints
the result, then shuts down. Requires ANTHROPIC_API_KEY and LANGCHAIN_API_KEY.
"""

import asyncio
import os

from temporalio.client import Client
from temporalio.contrib.langgraph import LangGraphPlugin
from temporalio.contrib.langsmith import LangSmithPlugin
from temporalio.worker import Worker

from langgraph_plugin.functional_api.langsmith_tracing.workflow import (
    ChatFunctionalWorkflow,
    activity_options,
    all_tasks,
    chat_entrypoint,
)


async def main() -> None:
    client = await Client.connect(
        os.environ.get("TEMPORAL_ADDRESS", "localhost:7233"),
        plugins=[LangSmithPlugin(add_temporal_runs=True)],
    )

    async with Worker(
        client,
        task_queue="langgraph-langsmith-functional",
        workflows=[ChatFunctionalWorkflow],
        plugins=[
            LangGraphPlugin(
                entrypoints={"chat": chat_entrypoint},
                tasks=all_tasks,
                activity_options=activity_options,
            )
        ],
    ):
        result = await client.execute_workflow(
            ChatFunctionalWorkflow.run,
            "What is the meaning of life?",
            id="langsmith-chat-functional-workflow",
            task_queue="langgraph-langsmith-functional",
        )
        print(f"Response: {result}")


if __name__ == "__main__":
    asyncio.run(main())
