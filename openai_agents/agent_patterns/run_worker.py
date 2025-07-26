from __future__ import annotations

import asyncio
from datetime import timedelta

from temporalio.client import Client
from temporalio.contrib.openai_agents import ModelActivityParameters, OpenAIAgentsPlugin
from temporalio.worker import Worker

from openai_agents.agent_patterns.workflows.agents_as_tools_workflow import (
    AgentsAsToolsWorkflow,
)
from openai_agents.agent_patterns.workflows.deterministic_workflow import (
    DeterministicWorkflow,
)
from openai_agents.agent_patterns.workflows.forcing_tool_use_workflow import (
    ForcingToolUseWorkflow,
)
from openai_agents.agent_patterns.workflows.input_guardrails_workflow import (
    InputGuardrailsWorkflow,
)
from openai_agents.agent_patterns.workflows.llm_as_a_judge_workflow import (
    LLMAsAJudgeWorkflow,
)
from openai_agents.agent_patterns.workflows.output_guardrails_workflow import (
    OutputGuardrailsWorkflow,
)
from openai_agents.agent_patterns.workflows.parallelization_workflow import (
    ParallelizationWorkflow,
)
from openai_agents.agent_patterns.workflows.routing_workflow import RoutingWorkflow


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
        task_queue="openai-agents-patterns-task-queue",
        workflows=[
            AgentsAsToolsWorkflow,
            DeterministicWorkflow,
            ParallelizationWorkflow,
            LLMAsAJudgeWorkflow,
            ForcingToolUseWorkflow,
            InputGuardrailsWorkflow,
            OutputGuardrailsWorkflow,
            RoutingWorkflow,
        ],
    )
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
