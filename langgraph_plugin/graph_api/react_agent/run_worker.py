"""Worker for the ReAct Agent sample.

Starts a Temporal worker that can execute ReActAgentWorkflow.
The LangGraphPlugin registers the graph and handles activity registration.

Prerequisites:
    - Temporal server running locally
    - OPENAI_API_KEY environment variable set
"""

import asyncio

from temporalio.client import Client
from temporalio.contrib.langgraph import LangGraphPlugin
from temporalio.envconfig import ClientConfig
from temporalio.worker import Worker

from langgraph_plugin.graph_api.react_agent.graph import build_react_agent
from langgraph_plugin.graph_api.react_agent.workflow import ReActAgentWorkflow


async def main() -> None:
    # Create the plugin with the ReAct agent graph registered
    plugin = LangGraphPlugin(
        graphs={"react_agent": build_react_agent},
    )

    # Connect to Temporal with the plugin
    config = ClientConfig.load_client_connect_config()
    config.setdefault("target_host", "localhost:7233")
    client = await Client.connect(**config, plugins=[plugin])

    # Create and run the worker
    # Note: Activities (LLM calls, tool executions) are automatically registered
    worker = Worker(
        client,
        task_queue="langgraph-react-agent",
        workflows=[ReActAgentWorkflow],
    )

    print("ReAct Agent worker started. Ctrl+C to exit.")
    print("Make sure OPENAI_API_KEY is set in your environment.")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
