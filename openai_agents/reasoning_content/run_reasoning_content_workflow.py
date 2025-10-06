#!/usr/bin/env python3

import asyncio
import os

from temporalio.client import Client
from temporalio.contrib.openai_agents import OpenAIAgentsPlugin

from openai_agents.reasoning_content.workflows.reasoning_content_workflow import (
    ReasoningContentWorkflow,
    ReasoningResult,
)


async def main():
    client = await Client.connect(
        "localhost:7233",
        plugins=[
            OpenAIAgentsPlugin(),
        ],
    )

    # Demo prompts that benefit from reasoning
    demo_prompts = [
        "What is the square root of 841? Please explain your reasoning.",
        "Explain the concept of recursion in programming",
        "Write a haiku about recursion in programming",
    ]

    model_name = os.getenv("EXAMPLE_MODEL_NAME") or "gpt-5"
    print(f"Using model: {model_name}")
    print("Note: This example requires a model that supports reasoning content.")
    print("You may need to use a specific model like gpt-5 or similar.\n")

    for i, prompt in enumerate(demo_prompts, 1):
        print(f"=== Example {i}: {prompt} ===")

        result: ReasoningResult = await client.execute_workflow(
            ReasoningContentWorkflow.run,
            args=[prompt, model_name],
            id=f"reasoning-content-{i}",
            task_queue="reasoning-content-task-queue",
        )

        print(f"\nPrompt: {result.prompt}")
        print("\nReasoning Content:")
        print(result.reasoning_content or "No reasoning content provided")
        print("\nRegular Content:")
        print(result.regular_content or "No regular content provided")
        print("-" * 50 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
