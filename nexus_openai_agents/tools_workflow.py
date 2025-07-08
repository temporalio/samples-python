from __future__ import annotations

from datetime import timedelta

from temporalio import workflow


# Import our activity, passing it through the sandbox
with workflow.unsafe.imports_passed_through():
    from agents import Agent, Runner
    from temporalio.contrib.openai_agents.temporal_tools import nexus_operation_as_tool

    from nexus_openai_agents.get_weather_service_handler import GetWeatherServiceHandler

@workflow.defn(sandboxed=False)
class ToolsWorkflow:
    @workflow.run
    async def run(self, question: str) -> str:
        agent = Agent(
            name="Tools Example Agent",
            instructions="You are a helpful agent.",
            tools=[
                nexus_operation_as_tool(
                    GetWeatherServiceHandler.get_weather,
                    service=GetWeatherServiceHandler,
                    schedule_to_close_timeout=timedelta(hours=10),
                    endpoint="weather-service",
                )
            ],
        )

        result = await Runner.run(agent, input=question)
        return result.final_output
