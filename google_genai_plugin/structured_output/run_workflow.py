"""Start the structured output workflow."""

import asyncio
import os

from temporalio.client import Client

from google_genai_plugin.structured_output.workflow import StructuredOutputWorkflow


async def main() -> None:
    client = await Client.connect(os.environ.get("TEMPORAL_ADDRESS", "localhost:7233"))

    recipe = await client.execute_workflow(
        StructuredOutputWorkflow.run,
        "Give me a simple recipe for avocado toast.",
        id="google-genai-structured-output",
        task_queue="google-genai-structured-output",
    )

    print(f"Recipe: {recipe.name}")
    print(f"Ingredients: {', '.join(recipe.ingredients)}")
    print("Steps:")
    for i, step in enumerate(recipe.steps, start=1):
        print(f"  {i}. {step}")


if __name__ == "__main__":
    asyncio.run(main())
