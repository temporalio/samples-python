from __future__ import annotations

from contextlib import aclosing
from dataclasses import dataclass

from temporalio import workflow
from temporalio.contrib.google_adk_agents import TemporalModel

with workflow.unsafe.imports_passed_through():
    from google.adk.agents import Agent
    from google.adk.runners import InMemoryRunner
    from google.genai import types


@dataclass
class AgentConfig:
    """Configuration for the loop agent."""

    name: str
    model: str = "gemini-2.5-flash"
    instruction: str = ""


@dataclass
class LoopInput:
    """Input for loop orchestration."""

    message: str
    agent_config: AgentConfig | None = None
    max_iterations: int = 5
    termination_phrase: str = "DONE"


@dataclass
class OrchestrationOutput:
    """Output from an orchestration workflow."""

    responses: list[str] | None = None
    final_response: str = ""
    iterations: int = 0

    def __post_init__(self):
        if self.responses is None:
            self.responses = []


@workflow.defn
class LoopWorkflow:
    """Run an agent repeatedly until a termination condition is met.

    Pattern: Iterative refinement — the agent writes, critiques itself,
    and stops when satisfied (output contains the termination phrase).
    """

    @workflow.run
    async def run(self, input: LoopInput) -> OrchestrationOutput:
        config = input.agent_config or AgentConfig(name="loop_agent")
        responses: list[str] = []
        current_message = input.message

        for _ in range(input.max_iterations):
            agent = Agent(
                name=config.name,
                model=TemporalModel(config.model),
                instruction=config.instruction,
            )

            app_name = f"loop_{config.name}"
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
                        parts=[types.Part.from_text(text=current_message)],
                    ),
                )
            ) as events:
                async for event in events:
                    if event.content and event.content.parts:
                        for part in event.content.parts:
                            if part.text:
                                result = part.text

            responses.append(result)

            if input.termination_phrase in result:
                break

            current_message = result

        return OrchestrationOutput(
            responses=responses,
            final_response=responses[-1] if responses else "",
            iterations=len(responses),
        )
