"""Worker for the ReAct Agent Functional API sample.

Starts a Temporal worker that can execute ReActAgentWorkflow.
The LangGraphFunctionalPlugin registers the entrypoint and handles activity registration.

Prerequisites:
    - Temporal server running locally
    - OPENAI_API_KEY environment variable set
"""

import asyncio
from datetime import timedelta

from temporalio.client import Client
from temporalio.contrib.langgraph import (
    LangGraphFunctionalPlugin,
    activity_options,
)
from temporalio.envconfig import ClientConfig
from temporalio.worker import Worker

from langgraph_plugin.functional_api.react_agent.entrypoint import (
    react_agent_entrypoint,
)
from langgraph_plugin.functional_api.react_agent.workflow import ReActAgentWorkflow


async def main() -> None:
    # Create the plugin with the ReAct agent entrypoint registered
    plugin = LangGraphFunctionalPlugin(
        entrypoints={"react_agent_entrypoint": react_agent_entrypoint},
        task_options={
            "call_model": activity_options(
                start_to_close_timeout=timedelta(minutes=2),
            ),
            "execute_tools": activity_options(
                start_to_close_timeout=timedelta(minutes=1),
            ),
        },
    )

    # Connect to Temporal with the plugin
    config = ClientConfig.load_client_connect_config()
    config.setdefault("target_host", "localhost:7233")
    client = await Client.connect(**config, plugins=[plugin])

    # Create and run the worker
    # Note: Task activities are automatically registered by the plugin
    worker = Worker(
        client,
        task_queue="langgraph-functional-react-agent",
        workflows=[ReActAgentWorkflow],
    )

    print("ReAct Agent worker started. Ctrl+C to exit.")
    print("Make sure OPENAI_API_KEY is set in your environment.")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
