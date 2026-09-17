"""Workflow that uses every durable MCP operation."""

from dataclasses import dataclass
from datetime import timedelta
from typing import Literal, cast

from mcp.types import TextContent, TextResourceContents
from temporalio import workflow
from temporalio.common import RetryPolicy
from temporalio.mcp import TemporalMCPClient

Transport = Literal["in-process", "stdio", "streamable-http"]
TRANSPORTS: tuple[Transport, ...] = ("in-process", "stdio", "streamable-http")


def client_name(transport: Transport) -> str:
    return f"sample-{transport}"


def task_queue(transport: Transport) -> str:
    return f"temporal-mcp-{transport}"


@dataclass
class MCPDemoResult:
    tools: list[str]
    tool_output: str
    prompts: list[str]
    prompt_output: str
    resources: list[str]
    resource_templates: list[str]
    resource_output: str


@workflow.defn
class MCPDemoWorkflow:
    @workflow.run
    async def run(self, transport: Transport) -> MCPDemoResult:
        client = TemporalMCPClient(
            client_name(transport),
            activity_config={
                "start_to_close_timeout": timedelta(seconds=10),
                "schedule_to_close_timeout": timedelta(seconds=30),
                "retry_policy": RetryPolicy(maximum_attempts=3),
            },
        )

        tools = await client.list_tools()
        # Tool discovery is cached in replay-safe Workflow state by default.
        assert await client.list_tools() is tools
        tool_result = await client.call_tool("echo", {"value": "durable execution"})
        prompts = await client.list_prompts()
        prompt = await client.get_prompt("greeting", {"name": "Temporal"})
        resources = await client.list_resources()
        resource_templates = await client.list_resource_templates()
        resource = await client.read_resource("sample://about")

        return MCPDemoResult(
            tools=[tool.name for tool in tools.tools],
            tool_output=cast(TextContent, tool_result.content[0]).text,
            prompts=[prompt.name for prompt in prompts.prompts],
            prompt_output=cast(TextContent, prompt.messages[0].content).text,
            resources=[resource.name for resource in resources.resources],
            resource_templates=[
                template.name for template in resource_templates.resource_templates
            ],
            resource_output=cast(TextResourceContents, resource.contents[0]).text,
        )
