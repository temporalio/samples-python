import asyncio

from temporalio.client import Client
from temporalio.contrib.openai_agents import OpenAIAgentsPlugin

from openai_agents.agent_patterns.workflows.input_guardrails_workflow import (
    InputGuardrailsWorkflow,
)


async def main():
    # Create client connected to server at the given address
    client = await Client.connect(
        "localhost:7233",
        plugins=[
            OpenAIAgentsPlugin(),
        ],
    )

    # Execute a workflow with a normal question (should pass)
    result1 = await client.execute_workflow(
        InputGuardrailsWorkflow.run,
        "What's the capital of California?",
        id="input-guardrails-workflow-normal",
        task_queue="openai-agents-patterns-task-queue",
    )
    print(f"Normal question result: {result1}")

    # Execute a workflow with a math homework question (should be blocked)
    result2 = await client.execute_workflow(
        InputGuardrailsWorkflow.run,
        "Can you help me solve for x: 2x + 5 = 11?",
        id="input-guardrails-workflow-blocked",
        task_queue="openai-agents-patterns-task-queue",
    )
    print(f"Math homework result: {result2}")


if __name__ == "__main__":
    asyncio.run(main())
