"""Execute the Reflection workflow."""

import asyncio

from temporalio.client import Client
from temporalio.envconfig import ClientConfig

from langgraph_samples.advanced.reflection.workflow import ReflectionWorkflow


async def main() -> None:
    config = ClientConfig.load_client_connect_config()
    config.setdefault("target_host", "localhost:7233")
    client = await Client.connect(**config)

    # A writing task that benefits from iterative refinement
    # The agent will:
    # 1. Generate initial content
    # 2. Critique and identify improvements
    # 3. Revise based on feedback
    # 4. Repeat until quality score >= 7 or max iterations
    result = await client.execute_workflow(
        ReflectionWorkflow.run,
        args=[
            "Write a short technical blog post introduction about why "
            "durable execution is important for AI agents. Target audience: "
            "software engineers. Length: 2-3 paragraphs.",
            3,  # max iterations
        ],
        id="reflection-workflow",
        task_queue="langgraph-reflection",
    )

    # Print the refinement journey
    print("\n" + "=" * 60)
    print("REFLECTION JOURNEY")
    print("=" * 60 + "\n")

    # Show critique history
    if result.get("critiques"):
        for i, critique in enumerate(result["critiques"], 1):
            print(f"Iteration {i} Critique:")
            print(f"  Score: {critique.quality_score}/10")
            print(f"  Strengths: {', '.join(critique.strengths[:2])}")
            print(f"  Weaknesses: {', '.join(critique.weaknesses[:2])}")
            print()

    # Print final content
    print("=" * 60)
    print("FINAL CONTENT")
    print("=" * 60 + "\n")
    print(result.get("final_content", result["current_draft"]))


if __name__ == "__main__":
    asyncio.run(main())
