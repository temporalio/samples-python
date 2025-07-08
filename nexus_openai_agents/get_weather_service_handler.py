"""
This file demonstrates how to implement a Nexus service.
"""

from __future__ import annotations

import uuid

from nexusrpc.handler import StartOperationContext, service_handler, sync_operation
from temporalio import nexus
from temporalio.nexus import WorkflowRunOperationContext, workflow_run_operation

from nexus_openai_agents.get_weather_service import (
    GetWeatherInput,
    GetWeatherService,
    Weather,
)

from nexus_openai_agents.get_weather_workflow import GetWeatherWorkflow


@service_handler(service=GetWeatherService)
class GetWeatherServiceHandler:
    @workflow_run_operation
    async def get_weather(
            self, ctx: WorkflowRunOperationContext, input: GetWeatherInput
    ) -> nexus.WorkflowHandle[Weather]:
        return await ctx.start_workflow(
            GetWeatherWorkflow.run,
            input.city,
            id=str(uuid.uuid4()),
        )
