"""Execute the Deep Research Functional API workflow."""

import asyncio

from temporalio.client import Client
from temporalio.envconfig import ClientConfig

from langgraph_plugin.functional_api.deep_research.workflow import DeepResearchWorkflow


async def main() -> None:
    config = ClientConfig.load_client_connect_config()
    config.setdefault("target_host", "localhost:7233")
    client = await Client.connect(**config)

    topic = "LangGraph multi-agent orchestration patterns"

    result = await client.execute_workflow(
        DeepResearchWorkflow.run,
        topic,
        id="deep-research-functional-workflow",
        task_queue="langgraph-functional-deep-research",
    )

    print(f"Topic: {result.get('topic')}")
    print(f"Iterations: {result.get('iterations')}")
    print(f"Total Searches: {result.get('total_searches')}")
    print(f"Relevant Results: {result.get('relevant_results')}")
    print(f"\nReport:\n{result.get('report')}")


if __name__ == "__main__":
    asyncio.run(main())
