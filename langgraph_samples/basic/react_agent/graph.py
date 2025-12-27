"""ReAct Agent Graph Definition.

This module builds a ReAct agent using LangGraph's create_react_agent
with Temporal-wrapped tools for durable execution.

Note: This module is only imported by the worker (not by the workflow).
LangGraph cannot be imported in the workflow sandbox.
"""

import os
from datetime import timedelta
from typing import Any

from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from temporalio.contrib.langgraph import temporal_tool

from langgraph_samples.basic.react_agent.tools import (
    calculate,
    get_weather,
    search_knowledge,
)


def build_react_agent() -> Any:
    """Build a ReAct agent with durable tool execution.

    This function creates a ReAct agent where tool invocations execute as
    Temporal activities with durability and automatic retries.

    The agent follows the ReAct pattern:
    1. Think: LLM decides what action to take
    2. Act: Execute the chosen tool
    3. Observe: Feed tool results back to LLM
    4. Repeat until done

    Returns:
        A compiled LangGraph that can be executed with ainvoke().
    """
    # Create the model
    model = ChatOpenAI(
        model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
        temperature=0,
    )

    # Wrap tools for durable execution as Temporal activities
    # Each tool call becomes a Temporal activity with its own timeout and retries
    tools = [
        temporal_tool(get_weather, start_to_close_timeout=timedelta(seconds=30)),
        temporal_tool(calculate, start_to_close_timeout=timedelta(seconds=10)),
        temporal_tool(search_knowledge, start_to_close_timeout=timedelta(seconds=30)),
    ]

    # Create the ReAct agent using LangGraph's prebuilt function
    # This creates a cyclic graph: agent -> tools -> agent (repeat until done)
    return create_react_agent(model, tools)
