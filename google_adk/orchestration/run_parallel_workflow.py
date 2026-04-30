import asyncio

from temporalio.client import Client
from temporalio.contrib.google_adk_agents import GoogleAdkPlugin

from google_adk.orchestration.workflows.parallel_workflow import (
    AgentConfig,
    ParallelInput,
    ParallelWorkflow,
)


async def main():
    client = await Client.connect(
        "localhost:7233",
        plugins=[GoogleAdkPlugin()],
    )

    question = "What are the pros and cons of microservices?"

    result = await client.execute_workflow(
        ParallelWorkflow.run,
        ParallelInput(
            messages=[question, question, question],
            agent_configs=[
                AgentConfig(
                    name="backend_engineer",
                    instruction="Answer from the perspective of a backend engineer focused on system design.",
                ),
                AgentConfig(
                    name="devops_engineer",
                    instruction="Answer from the perspective of a DevOps engineer focused on deployment and operations.",
                ),
                AgentConfig(
                    name="tech_lead",
                    instruction="Answer from the perspective of a tech lead focused on team productivity.",
                ),
            ],
        ),
        id="google-adk-parallel-workflow",
        task_queue="google-adk-orchestration-task-queue",
    )
    print(f"Responses collected: {result.iterations}")
    for i, response in enumerate(result.responses):
        print(f"\n--- Perspective {i + 1} ---")
        print(response[:300] + "..." if len(response) > 300 else response)


if __name__ == "__main__":
    asyncio.run(main())
