"""Tests for the Sequential Thinking MCP Server workflow."""

import pytest
from mcp.types import (
    CallToolRequest,
    CallToolRequestParams,
    ListToolsRequest,
    TextContent,
)
from mcp_sequential_thinking.mcp_server.workflow import (
    SequentialThinkingMCPServerWorkflow,
)
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker


@pytest.mark.asyncio
async def test_list_tools():
    """Test that list_tools returns the sequential thinking tool."""
    async with await WorkflowEnvironment.start_local() as env:
        async with Worker(
            env.client,
            task_queue="test-sequential-thinking",
            workflows=[SequentialThinkingMCPServerWorkflow],
        ):
            # Start the workflow
            handle = await env.client.start_workflow(
                SequentialThinkingMCPServerWorkflow.start,
                id="test-workflow-1",
                task_queue="test-sequential-thinking",
            )

            # Query for tools
            request = ListToolsRequest(method="tools/list")
            result = await handle.query(
                SequentialThinkingMCPServerWorkflow.list_tools, request
            )

            assert len(result.tools) == 1
            assert result.tools[0].name == "sequentialthinking"
            assert result.tools[0].description is not None
            assert (
                "dynamic and reflective problem-solving" in result.tools[0].description
            )

            # Stop the workflow
            await handle.execute_update(SequentialThinkingMCPServerWorkflow.stop)


@pytest.mark.asyncio
async def test_call_tool_valid_thought():
    """Test calling the sequential thinking tool with valid input."""
    async with await WorkflowEnvironment.start_local() as env:
        async with Worker(
            env.client,
            task_queue="test-sequential-thinking",
            workflows=[SequentialThinkingMCPServerWorkflow],
        ):
            # Start the workflow
            handle = await env.client.start_workflow(
                SequentialThinkingMCPServerWorkflow.start,
                id="test-workflow-2",
                task_queue="test-sequential-thinking",
            )

            # Call the tool with valid thought
            request = CallToolRequest(
                method="tools/call",
                params=CallToolRequestParams(
                    name="sequentialthinking",
                    arguments={
                        "thought": "Let me break down this problem step by step",
                        "thoughtNumber": 1,
                        "totalThoughts": 3,
                        "nextThoughtNeeded": True,
                    },
                ),
            )

            result = await handle.execute_update(
                SequentialThinkingMCPServerWorkflow.call_tool, request
            )

            assert not result.isError
            assert len(result.content) == 1
            assert result.content[0].type == "text"

            # Parse the JSON response
            import json

            assert isinstance(result.content[0], TextContent)
            response_data = json.loads(result.content[0].text)
            assert response_data["thoughtNumber"] == 1
            assert response_data["totalThoughts"] == 3
            assert response_data["nextThoughtNeeded"] is True
            assert response_data["thoughtHistoryLength"] == 1
            assert response_data["branches"] == []

            # Stop the workflow
            await handle.execute_update(SequentialThinkingMCPServerWorkflow.stop)


@pytest.mark.asyncio
async def test_call_tool_with_branch():
    """Test sequential thinking with branching."""
    async with await WorkflowEnvironment.start_local() as env:
        async with Worker(
            env.client,
            task_queue="test-sequential-thinking",
            workflows=[SequentialThinkingMCPServerWorkflow],
        ):
            # Start the workflow
            handle = await env.client.start_workflow(
                SequentialThinkingMCPServerWorkflow.start,
                id="test-workflow-3",
                task_queue="test-sequential-thinking",
            )

            # First thought
            request1 = CallToolRequest(
                method="tools/call",
                params=CallToolRequestParams(
                    name="sequentialthinking",
                    arguments={
                        "thought": "Initial approach to the problem",
                        "thoughtNumber": 1,
                        "totalThoughts": 2,
                        "nextThoughtNeeded": True,
                    },
                ),
            )
            await handle.execute_update(
                SequentialThinkingMCPServerWorkflow.call_tool, request1
            )

            # Branch from first thought
            request2 = CallToolRequest(
                method="tools/call",
                params=CallToolRequestParams(
                    name="sequentialthinking",
                    arguments={
                        "thought": "Alternative approach branching from thought 1",
                        "thoughtNumber": 2,
                        "totalThoughts": 3,
                        "nextThoughtNeeded": False,
                        "branchFromThought": 1,
                        "branchId": "alternative-1",
                    },
                ),
            )

            result = await handle.execute_update(
                SequentialThinkingMCPServerWorkflow.call_tool, request2
            )

            import json

            assert isinstance(result.content[0], TextContent)
            response_data = json.loads(result.content[0].text)
            assert response_data["thoughtHistoryLength"] == 2
            assert "alternative-1" in response_data["branches"]

            # Stop the workflow
            await handle.execute_update(SequentialThinkingMCPServerWorkflow.stop)


@pytest.mark.asyncio
async def test_call_tool_invalid_input():
    """Test error handling for invalid input."""
    async with await WorkflowEnvironment.start_local() as env:
        async with Worker(
            env.client,
            task_queue="test-sequential-thinking",
            workflows=[SequentialThinkingMCPServerWorkflow],
        ):
            # Start the workflow
            handle = await env.client.start_workflow(
                SequentialThinkingMCPServerWorkflow.start,
                id="test-workflow-4",
                task_queue="test-sequential-thinking",
            )

            # Call with missing required field
            request = CallToolRequest(
                method="tools/call",
                params=CallToolRequestParams(
                    name="sequentialthinking",
                    arguments={
                        "thought": "Missing thoughtNumber",
                        "totalThoughts": 3,
                        "nextThoughtNeeded": True,
                    },
                ),
            )

            result = await handle.execute_update(
                SequentialThinkingMCPServerWorkflow.call_tool, request
            )

            assert result.isError
            assert len(result.content) == 1

            import json

            assert isinstance(result.content[0], TextContent)
            error_data = json.loads(result.content[0].text)
            assert error_data["status"] == "failed"
            assert "thoughtNumber" in error_data["error"]

            # Stop the workflow
            await handle.execute_update(SequentialThinkingMCPServerWorkflow.stop)


@pytest.mark.asyncio
async def test_call_unknown_tool():
    """Test calling an unknown tool."""
    async with await WorkflowEnvironment.start_local() as env:
        async with Worker(
            env.client,
            task_queue="test-sequential-thinking",
            workflows=[SequentialThinkingMCPServerWorkflow],
        ):
            # Start the workflow
            handle = await env.client.start_workflow(
                SequentialThinkingMCPServerWorkflow.start,
                id="test-workflow-5",
                task_queue="test-sequential-thinking",
            )

            # Call unknown tool
            request = CallToolRequest(
                method="tools/call",
                params=CallToolRequestParams(name="unknown-tool", arguments={}),
            )

            result = await handle.execute_update(
                SequentialThinkingMCPServerWorkflow.call_tool, request
            )

            assert result.isError
            assert isinstance(result.content[0], TextContent)
            assert "Unknown tool: unknown-tool" in result.content[0].text

            # Stop the workflow
            await handle.execute_update(SequentialThinkingMCPServerWorkflow.stop)


@pytest.mark.asyncio
async def test_thought_number_adjustment():
    """Test that totalThoughts is adjusted when thoughtNumber exceeds it."""
    async with await WorkflowEnvironment.start_local() as env:
        async with Worker(
            env.client,
            task_queue="test-sequential-thinking",
            workflows=[SequentialThinkingMCPServerWorkflow],
        ):
            # Start the workflow
            handle = await env.client.start_workflow(
                SequentialThinkingMCPServerWorkflow.start,
                id="test-workflow-6",
                task_queue="test-sequential-thinking",
            )

            # Call with thoughtNumber > totalThoughts
            request = CallToolRequest(
                method="tools/call",
                params=CallToolRequestParams(
                    name="sequentialthinking",
                    arguments={
                        "thought": "Extended thinking beyond initial estimate",
                        "thoughtNumber": 5,
                        "totalThoughts": 3,
                        "nextThoughtNeeded": False,
                    },
                ),
            )

            result = await handle.execute_update(
                SequentialThinkingMCPServerWorkflow.call_tool, request
            )

            import json

            assert isinstance(result.content[0], TextContent)
            response_data = json.loads(result.content[0].text)
            # totalThoughts should be adjusted to match thoughtNumber
            assert response_data["totalThoughts"] == 5
            assert response_data["thoughtNumber"] == 5

            # Stop the workflow
            await handle.execute_update(SequentialThinkingMCPServerWorkflow.stop)
