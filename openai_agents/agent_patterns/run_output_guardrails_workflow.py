import asyncio

from temporalio.client import Client
from temporalio.contrib.openai_agents import OpenAIAgentsPlugin

from openai_agents.agent_patterns.workflows.output_guardrails_workflow import (
    OutputGuardrailsWorkflow,
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
        OutputGuardrailsWorkflow.run,
        "What's the capital of California?",
        id="output-guardrails-workflow-normal",
        task_queue="openai-agents-patterns-task-queue",
    )
    print(f"Normal question result: {result1}")

    # Execute a workflow with input that might trigger sensitive data output
    result2 = await client.execute_workflow(
        OutputGuardrailsWorkflow.run,
        "My phone number is 650-123-4567. Where do you think I live?",
        id="output-guardrails-workflow-sensitive",
        task_queue="openai-agents-patterns-task-queue",
    )
    print(f"Sensitive data result: {result2}")


if __name__ == "__main__":
    asyncio.run(main())
