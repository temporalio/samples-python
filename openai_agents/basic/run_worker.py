from __future__ import annotations

import asyncio
from datetime import timedelta

from temporalio.client import Client
from temporalio.contrib.openai_agents import ModelActivityParameters, OpenAIAgentsPlugin
from temporalio.worker import Worker

from openai_agents.basic.activities.get_weather_activity import get_weather
from openai_agents.basic.activities.image_activities import read_image_as_base64
from openai_agents.basic.activities.math_activities import (
    multiply_by_two,
    random_number,
)
from openai_agents.basic.workflows.agent_lifecycle_workflow import (
    AgentLifecycleWorkflow,
)
from openai_agents.basic.workflows.dynamic_system_prompt_workflow import (
    DynamicSystemPromptWorkflow,
)
from openai_agents.basic.workflows.hello_world_workflow import HelloWorldAgent
from openai_agents.basic.workflows.lifecycle_workflow import LifecycleWorkflow
from openai_agents.basic.workflows.local_image_workflow import LocalImageWorkflow
from openai_agents.basic.workflows.non_strict_output_workflow import (
    NonStrictOutputWorkflow,
)
from openai_agents.basic.workflows.previous_response_id_workflow import (
    PreviousResponseIdWorkflow,
)
from openai_agents.basic.workflows.remote_image_workflow import RemoteImageWorkflow
from openai_agents.basic.workflows.tools_workflow import ToolsWorkflow


async def main():
    # Create client connected to server at the given address
    client = await Client.connect(
        "localhost:7233",
        plugins=[
            OpenAIAgentsPlugin(
                model_params=ModelActivityParameters(
                    start_to_close_timeout=timedelta(seconds=30)
                )
            ),
        ],
    )

    worker = Worker(
        client,
        task_queue="openai-agents-task-queue",
        workflows=[
            HelloWorldAgent,
            ToolsWorkflow,
            AgentLifecycleWorkflow,
            DynamicSystemPromptWorkflow,
            NonStrictOutputWorkflow,
            LocalImageWorkflow,
            RemoteImageWorkflow,
            LifecycleWorkflow,
            PreviousResponseIdWorkflow,
        ],
        activities=[
            get_weather,
            multiply_by_two,
            random_number,
            read_image_as_base64,
        ],
    )
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
