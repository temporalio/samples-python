from __future__ import annotations

import asyncio
from contextlib import aclosing
from dataclasses import dataclass, field

from temporalio import workflow
from temporalio.contrib.google_adk_agents import TemporalModel

with workflow.unsafe.imports_passed_through():
    from google.adk.agents import Agent
    from google.adk.runners import InMemoryRunner
    from google.genai import types


@dataclass
class AgentConfig:
    """Configuration for a single agent."""

    name: str
    model: str = "gemini-2.5-flash"
    instruction: str = ""


@dataclass
class ParallelInput:
    """Input for parallel orchestration."""

    messages: list[str] = field(default_factory=list)
    agent_configs: list[AgentConfig] = field(default_factory=list)


@dataclass
class OrchestrationOutput:
    """Output from an orchestration workflow."""

    responses: list[str] = field(default_factory=list)
    final_response: str = ""
    iterations: int = 0


async def _run_single_agent(config: AgentConfig, message: str) -> str:
    """Helper to run a single ADK agent and return its text output."""
    agent = Agent(
        name=config.name,
        model=TemporalModel(config.model),
        instruction=config.instruction,
    )

    app_name = f"parallel_{config.name}"
    runner = InMemoryRunner(agent=agent, app_name=app_name)
    session = await runner.session_service.create_session(
        user_id="user", app_name=app_name
    )

    result = ""
    async with aclosing(
        runner.run_async(
            user_id="user",
            session_id=session.id,
            new_message=types.Content(
                role="user",
                parts=[types.Part.from_text(text=message)],
            ),
        )
    ) as events:
        async for event in events:
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        result = part.text

    return result


@workflow.defn
class ParallelWorkflow:
    """Run agents concurrently, collect all results.

    Pattern: Multiple perspectives on the same question.
    All agents run simultaneously via asyncio.gather.
    """

    @workflow.run
    async def run(self, input: ParallelInput) -> OrchestrationOutput:
        pairs = list(zip(input.agent_configs, input.messages, strict=False))

        tasks = [
            asyncio.ensure_future(_run_single_agent(config, message))
            for config, message in pairs
        ]
        results: list[str] = await asyncio.gather(*tasks)

        return OrchestrationOutput(
            responses=list(results),
            final_response=results[-1] if results else "",
            iterations=len(results),
        )
