import asyncio

from temporalio.client import Client
from temporalio.contrib.google_adk_agents import GoogleAdkPlugin

from google_adk.orchestration.workflows.loop_workflow import (
    AgentConfig,
    LoopInput,
    LoopWorkflow,
)


async def main():
    client = await Client.connect(
        "localhost:7233",
        plugins=[GoogleAdkPlugin()],
    )

    result = await client.execute_workflow(
        LoopWorkflow.run,
        LoopInput(
            message=(
                "Write a haiku about Temporal.io. After writing it, "
                "evaluate if it's good. If it is, respond with DONE. "
                "If not, try again."
            ),
            agent_config=AgentConfig(
                name="poet",
                instruction="You are a poet who writes and critiques haiku. Be self-critical.",
            ),
            max_iterations=5,
            termination_phrase="DONE",
        ),
        id="google-adk-loop-workflow",
        task_queue="google-adk-orchestration-task-queue",
    )
    print(f"Iterations: {result.iterations}")
    for i, response in enumerate(result.responses):
        print(f"\n--- Iteration {i + 1} ---")
        print(response[:300] + "..." if len(response) > 300 else response)


if __name__ == "__main__":
    asyncio.run(main())
