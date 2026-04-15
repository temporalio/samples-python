"""Start the LangSmith tracing chat workflow (Functional API).

Requires ANTHROPIC_API_KEY and LANGCHAIN_API_KEY environment variables.
"""

import asyncio
import os

from temporalio.client import Client
from temporalio.contrib.langsmith import LangSmithPlugin

from langgraph_plugin.functional_api.langsmith_tracing.workflow import (
    ChatFunctionalWorkflow,
)


async def main() -> None:
    client = await Client.connect(
        os.environ.get("TEMPORAL_ADDRESS", "localhost:7233"),
        plugins=[LangSmithPlugin(add_temporal_runs=True)],
    )

    result = await client.execute_workflow(
        ChatFunctionalWorkflow.run,
        "What is the meaning of life?",
        id="langsmith-chat-functional-workflow",
        task_queue="langgraph-langsmith-functional",
    )

    print(f"Response: {result}")


if __name__ == "__main__":
    asyncio.run(main())
