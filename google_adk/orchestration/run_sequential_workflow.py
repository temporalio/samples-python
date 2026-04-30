import asyncio

from temporalio.client import Client
from temporalio.contrib.google_adk_agents import GoogleAdkPlugin

from google_adk.orchestration.workflows.sequential_workflow import (
    AgentConfig,
    SequentialInput,
    SequentialWorkflow,
)


async def main():
    client = await Client.connect(
        "localhost:7233",
        plugins=[GoogleAdkPlugin()],
    )

    result = await client.execute_workflow(
        SequentialWorkflow.run,
        SequentialInput(
            message="Explain how garbage collection works in Python",
            agent_configs=[
                AgentConfig(
                    name="researcher",
                    instruction="Research the topic and provide key facts and technical details.",
                ),
                AgentConfig(
                    name="writer",
                    instruction="Take the research and write a clear, well-structured explanation for developers.",
                ),
                AgentConfig(
                    name="editor",
                    instruction="Edit the text for clarity and conciseness. Keep it under 200 words.",
                ),
            ],
        ),
        id="google-adk-sequential-workflow",
        task_queue="google-adk-orchestration-task-queue",
    )
    print(f"Steps completed: {result.iterations}")
    print(f"Final response:\n{result.final_response}")


if __name__ == "__main__":
    asyncio.run(main())
