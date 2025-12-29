"""Execute the Supervisor Multi-Agent workflow."""

import asyncio

from temporalio.client import Client
from temporalio.envconfig import ClientConfig

from langgraph_samples.multi_agent.supervisor.workflow import SupervisorWorkflow


async def main() -> None:
    config = ClientConfig.load_client_connect_config()
    config.setdefault("target_host", "localhost:7233")
    client = await Client.connect(**config)

    # This request requires multiple agents:
    # 1. Researcher to find information about AI trends
    # 2. Analyst to process/analyze the data
    # 3. Writer to create a summary
    request = (
        "Research the latest AI trends in 2024, analyze which trends are most "
        "impactful for enterprise software development, and write a brief "
        "executive summary (2-3 paragraphs)."
    )

    print("Executing supervisor multi-agent workflow...")
    print(f"Request: {request}")
    print()

    result = await client.execute_workflow(
        SupervisorWorkflow.run,
        request,
        id="supervisor-workflow",
        task_queue="langgraph-supervisor",
    )

    # Print the final response
    print("=" * 60)
    print("FINAL RESPONSE:")
    print("=" * 60)

    # Get the last assistant message
    messages = result.get("messages", [])
    for msg in reversed(messages):
        # Handle both dict and object formats
        if isinstance(msg, dict):
            if msg.get("role") == "assistant" or msg.get("type") == "ai":
                content = msg.get("content", "")
                if content and not content.startswith("["):  # Skip tool outputs
                    print(content)
                    break
        elif hasattr(msg, "content"):
            msg_type = getattr(msg, "type", "")
            if msg_type == "ai" and msg.content:
                print(msg.content)
                break


if __name__ == "__main__":
    asyncio.run(main())
