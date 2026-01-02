"""Execute the Plan-and-Execute Functional API workflow."""

import asyncio

from temporalio.client import Client
from temporalio.envconfig import ClientConfig

from langgraph_plugin.functional_api.plan_and_execute.workflow import (
    PlanExecuteWorkflow,
)


async def main() -> None:
    config = ClientConfig.load_client_connect_config()
    config.setdefault("target_host", "localhost:7233")
    client = await Client.connect(**config)

    objective = "Look up information about LangGraph, then calculate what 25 * 4 equals, and analyze the combined findings."

    result = await client.execute_workflow(
        PlanExecuteWorkflow.run,
        objective,
        id="plan-execute-functional-workflow",
        task_queue="langgraph-functional-plan-execute",
    )

    print(f"Objective: {result.get('objective')}")
    print(f"\nPlan Steps: {len(result.get('plan', {}).get('steps', []))}")
    print(f"\nFinal Response:\n{result.get('final_response')}")


if __name__ == "__main__":
    asyncio.run(main())
