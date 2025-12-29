"""Execute the Deep Research workflow."""

import asyncio

from temporalio.client import Client
from temporalio.envconfig import ClientConfig

from langgraph_samples.deep_research.workflow import DeepResearchWorkflow


async def main() -> None:
    config = ClientConfig.load_client_connect_config()
    config.setdefault("target_host", "localhost:7233")
    client = await Client.connect(**config)

    # Research topic that will trigger multiple search queries
    # The agent will:
    # 1. Plan queries about LangGraph, Temporal, durable execution
    # 2. Execute searches in parallel
    # 3. Evaluate results and possibly iterate
    # 4. Synthesize a comprehensive research report
    result = await client.execute_workflow(
        DeepResearchWorkflow.run,
        "How do LangGraph and Temporal work together for durable AI agents?",
        id="deep-research-workflow",
        task_queue="langgraph-deep-research",
    )

    # Print the research report (last message)
    print("\n" + "=" * 60)
    print("RESEARCH REPORT")
    print("=" * 60 + "\n")
    print(result["messages"][-1]["content"])


if __name__ == "__main__":
    asyncio.run(main())
