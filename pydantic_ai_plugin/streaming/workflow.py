from dataclasses import dataclass
from datetime import timedelta

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from pydantic_ai import Agent
    from pydantic_ai.durable_exec.temporal import (
        AgentEventStream,
        PydanticAIWorkflow,
        TemporalDurability,
        WorkflowStreamTopic,
    )
    from pydantic_ai.messages import PartDeltaEvent
    from pydantic_ai.models.test import TestModel


@dataclass
class StreamingInput:
    prompt: str
    model: str | None = None
    drain_timeout_seconds: float = 30


topic = WorkflowStreamTopic(
    "agent-events",
    events=lambda event: not isinstance(event, PartDeltaEvent),
)
durability = TemporalDurability(event_stream_topic=topic)
agent = Agent(
    TestModel(custom_output_text="The durable response is complete."),
    name="workflow_streaming",
    capabilities=[durability],
)


@workflow.defn
class StreamingWorkflow(PydanticAIWorkflow):
    __pydantic_ai_agents__ = [agent]

    @workflow.init
    def __init__(self, input: StreamingInput) -> None:
        self.events = AgentEventStream(
            drain_timeout=timedelta(seconds=input.drain_timeout_seconds)
        )

    @workflow.run
    async def run(self, input: StreamingInput) -> str:
        async with self.events:
            result = await agent.run(input.prompt, model=input.model)
        return result.output
