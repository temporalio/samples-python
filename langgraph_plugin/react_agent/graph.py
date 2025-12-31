"""ReAct Agent Graph Definition.

This module builds an agent using LangChain's create_agent.
Each node (agent reasoning, tool execution) runs as a Temporal activity,
providing automatic retries and failure recovery.

Note: This module is only imported by the worker (not by the workflow).
LangGraph cannot be imported in the workflow sandbox.
"""

import os
from typing import Any

from langchain_openai import ChatOpenAI

from langchain.agents import create_agent
from langgraph_plugin.react_agent.tools import calculate, get_weather


def build_react_agent() -> Any:
    """Build an agent with durable execution.

    Uses LangChain's create_agent which creates a graph with:
    - An "agent" node that calls the LLM to decide actions
    - A "tools" node that executes the requested tools

    The Temporal integration runs each node as a separate activity:
    - Progress is saved after each node completes
    - Failed nodes can be automatically retried
    - If the worker crashes, execution resumes from the last completed node

    The agent follows the ReAct pattern:
    1. Think: LLM decides what action to take (agent node)
    2. Act: Execute the chosen tool (tools node)
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

    # Define the tools - get_weather and calculate
    # The sample query requires both: get weather, then calculate F to C conversion
    tools = [get_weather, calculate]

    # Create the agent using LangChain's create_agent
    # The Temporal integration will run each node as an activity
    return create_agent(model, tools)
