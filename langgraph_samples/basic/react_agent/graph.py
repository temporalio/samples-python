"""ReAct Agent Graph Definition.

This module builds a ReAct agent using Temporal's create_durable_react_agent
for fully durable execution of both LLM calls and tool invocations.

Note: This module is only imported by the worker (not by the workflow).
LangGraph cannot be imported in the workflow sandbox.
"""

import os
from datetime import timedelta
from typing import Any

from langchain_openai import ChatOpenAI

from temporalio.contrib.langgraph import activity_options, create_durable_react_agent

from langgraph_samples.basic.react_agent.tools import (
    calculate,
    get_weather,
    search_knowledge,
)


def build_react_agent() -> Any:
    """Build a ReAct agent with fully durable execution.

    Uses Temporal's create_durable_react_agent which automatically wraps:
    - The model with temporal_model() for durable LLM calls
    - The tools with temporal_tool() for durable tool execution

    The agent nodes run inline in the workflow while model and tool
    calls execute as separate Temporal activities with their own
    timeouts and retry policies.

    The agent follows the ReAct pattern:
    1. Think: LLM decides what action to take (durable activity)
    2. Act: Execute the chosen tool (durable activity)
    3. Observe: Feed tool results back to LLM
    4. Repeat until done

    Returns:
        A compiled LangGraph that can be executed with ainvoke().
    """
    # Create the model - will be automatically wrapped for durable execution
    model = ChatOpenAI(
        model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
        temperature=0,
    )

    # Tools - will be automatically wrapped for durable execution
    tools = [get_weather, calculate, search_knowledge]

    # Create the ReAct agent using Temporal's durable version
    # This automatically wraps model and tools, and marks nodes to run
    # inline in the workflow (with model/tool calls as activities)
    return create_durable_react_agent(
        model,
        tools,
        model_activity_options=activity_options(
            start_to_close_timeout=timedelta(minutes=2),
        ),
        tool_activity_options=activity_options(
            start_to_close_timeout=timedelta(seconds=30),
        ),
    )
