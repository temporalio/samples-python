import asyncio

from temporalio.client import Client
from temporalio.contrib.openai_agents import OpenAIAgentsPlugin

from openai_agents.agent_patterns.workflows.llm_as_a_judge_workflow import (
    LLMAsAJudgeWorkflow,
)


async def main():
    # Create client connected to server at the given address
    client = await Client.connect(
        "localhost:7233",
        plugins=[
            OpenAIAgentsPlugin(),
        ],
    )

    # Execute a workflow
    result = await client.execute_workflow(
        LLMAsAJudgeWorkflow.run,
        "A thrilling adventure story about pirates searching for treasure",
        id="llm-as-a-judge-workflow-example",
        task_queue="openai-agents-patterns-task-queue",
    )
    print(f"Result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
