"""Tests for the LLM-powered agent workflow."""

import os
import pytest
from temporalio.client import Client
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from mcp_sequential_thinking.agent_workflow_with_llm import AgentWorkflowWithLLM
from mcp_sequential_thinking.llm_activity import call_llm, parse_json_response
from mcp_sequential_thinking.mcp_server.nexus_service import (
    MCPServerNexusServiceHandler,
)
from mcp_sequential_thinking.mcp_server.workflow import (
    SequentialThinkingMCPServerWorkflow,
)

from .helpers import create_nexus_endpoint, delete_nexus_endpoint


@pytest.mark.asyncio
async def test_agent_workflow_with_llm(client: Client, env: WorkflowEnvironment):
    """Test the agent workflow with real LLM calls."""
    if env.supports_time_skipping:
        pytest.skip("Nexus tests don't work under the Java test server")
    
    # Skip if no API key is available
    if not os.environ.get("ANTHROPIC_API_KEY"):
        pytest.skip("ANTHROPIC_API_KEY not set")
    
    task_queue = "test-mcp-llm-task-queue"
    nexus_endpoint = "mcp-sequential-thinking-nexus-endpoint"
    
    create_response = await create_nexus_endpoint(
        name=nexus_endpoint,
        task_queue=task_queue,
        client=client,
    )
    
    try:
        async with Worker(
            client,
            task_queue=task_queue,
            workflows=[AgentWorkflowWithLLM, SequentialThinkingMCPServerWorkflow],
            activities=[call_llm, parse_json_response],
            nexus_service_handlers=[MCPServerNexusServiceHandler()],
        ):
            # Test with a simple problem
            handle = await client.start_workflow(
                AgentWorkflowWithLLM.run,
                "What is 15 + 27?",
                id="test-workflow-llm",
                task_queue=task_queue,
            )
            
            result = await handle.result()
            
            # Verify the result contains expected elements
            assert "Problem: What is 15 + 27?" in result
            assert "Thinking Process:" in result
            assert "Final Answer:" in result
            assert "42" in result  # The correct answer
            
    finally:
        await delete_nexus_endpoint(
            id=create_response.endpoint.id,
            version=create_response.endpoint.version,
            client=client,
        )
