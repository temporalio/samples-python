"""Start the long-running research agent workflow."""

import asyncio
import os

from temporalio.client import Client

from deepagents_plugin.continue_as_new.workflow import LongResearchAgent


async def main() -> None:
    client = await Client.connect(os.environ.get("TEMPORAL_ADDRESS", "localhost:7233"))

    result = await client.execute_workflow(
        LongResearchAgent.run,
        # The workflow's first arg is the messages mapping (run_deep_agent's
        # continue-as-new contract), not a bare question string.
        {
            "messages": [
                {
                    "role": "user",
                    "content": (
                        "Research the tradeoffs between Raft and Paxos and "
                        "summarize them."
                    ),
                }
            ]
        },
        id="deepagents-continue-as-new",
        task_queue="deepagents-continue-as-new",
    )

    print(f"Result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
