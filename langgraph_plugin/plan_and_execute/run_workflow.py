"""Execute the Plan-and-Execute workflow."""

import asyncio

from temporalio.client import Client
from temporalio.envconfig import ClientConfig

from langgraph_plugin.plan_and_execute.workflow import (
    PlanAndExecuteWorkflow,
)


async def main() -> None:
    config = ClientConfig.load_client_connect_config()
    config.setdefault("target_host", "localhost:7233")
    client = await Client.connect(**config)

    # A task that requires planning and multiple steps
    # The agent will:
    # 1. Create a plan with specific steps
    # 2. Execute each step using tools (lookup, calculate, analyze)
    # 3. Compile results into a final answer
    result = await client.execute_workflow(
        PlanAndExecuteWorkflow.run,
        "What is LangGraph and how does it compare to other agent frameworks? "
        "Calculate how many more features it has than a basic ReAct agent.",
        id="plan-execute-workflow",
        task_queue="langgraph-plan-execute",
    )

    # Print the final response
    print("\n" + "=" * 60)
    print("EXECUTION RESULT")
    print("=" * 60 + "\n")

    # Print step results if available
    if result.get("step_results"):
        print("Steps Executed:")
        for step in result["step_results"]:
            print(f"  {step.step_number}. {step.description}")
            print(f"     Result: {step.result[:100]}...")
        print()

    # Print final message
    print("Final Answer:")
    print(result["messages"][-1]["content"])


if __name__ == "__main__":
    asyncio.run(main())
