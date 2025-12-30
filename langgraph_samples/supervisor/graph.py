"""Supervisor Multi-Agent Graph Definition.

This module implements a supervisor agent that coordinates specialized worker agents.
The supervisor routes tasks to appropriate agents (researcher, writer, analyst) and
aggregates their results.

Architecture:
- Supervisor: Central coordinator that decides which agent should handle each task
- Researcher: Agent with web search capabilities for gathering information
- Writer: Agent specialized in content creation and summarization
- Analyst: Agent for data analysis and mathematical operations

The Temporal LangGraph plugin runs each agent's nodes as separate activities,
providing durability and automatic retries for the entire multi-agent system.

Note: This module is only imported by the worker (not by the workflow).
LangGraph cannot be imported in the workflow sandbox.
"""

import os
from typing import Any

from langchain_openai import ChatOpenAI
from langgraph_supervisor import create_supervisor

from langchain.agents import create_agent

# --- Tools for specialized agents ---


def web_search(query: str) -> str:
    """Search the web for information.

    This is a mock implementation. In production, you would integrate
    with a real search API like Tavily, SerpAPI, or similar.
    """
    # Mock search results for demonstration
    mock_results = {
        "ai trends 2024": (
            "Key AI trends in 2024:\n"
            "1. Multimodal AI models combining text, image, and video\n"
            "2. AI agents and autonomous systems\n"
            "3. Small language models for edge deployment\n"
            "4. AI in scientific discovery\n"
            "5. Responsible AI and governance frameworks"
        ),
        "temporal workflow": (
            "Temporal is a durable execution platform:\n"
            "- Workflows survive failures and can run for years\n"
            "- Activities are retried automatically on failure\n"
            "- Built-in support for signals, queries, and timers\n"
            "- Used by companies like Netflix, Snap, and Stripe"
        ),
        "langgraph multi-agent": (
            "LangGraph multi-agent patterns:\n"
            "- Supervisor: Central coordinator routes tasks to specialists\n"
            "- Swarm: Agents hand off to each other dynamically\n"
            "- Hierarchical: Team supervisors under a top-level coordinator\n"
            "- Collaborative: Agents work together on shared state"
        ),
    }

    # Try to match query to mock results
    query_lower = query.lower()
    for key, result in mock_results.items():
        if any(word in query_lower for word in key.split()):
            return result

    return f"Search results for '{query}': No specific results found. Please try a different query."


def write_content(topic: str, style: str = "informative") -> str:
    """Write content on a given topic.

    This is a mock implementation. The actual content generation
    would be handled by the LLM in the agent's reasoning.
    """
    return f"[Content draft on '{topic}' in {style} style - LLM will generate actual content]"


def summarize(text: str, max_length: int = 100) -> str:
    """Summarize the given text.

    This is a mock implementation. The actual summarization
    would be handled by the LLM in the agent's reasoning.
    """
    return f"[Summary of {len(text)} characters, max {max_length} words - LLM will generate]"


def calculate(expression: str) -> str:
    """Evaluate a mathematical expression safely.

    Supports basic arithmetic operations.
    """
    try:
        # Only allow safe mathematical operations
        allowed_chars = set("0123456789+-*/.() ")
        if not all(c in allowed_chars for c in expression):
            return "Error: Invalid characters in expression. Only numbers and +-*/.() are allowed."

        result = eval(expression)  # noqa: S307
        return str(result)
    except Exception as e:
        return f"Error evaluating '{expression}': {e}"


def analyze_data(data: str, analysis_type: str = "summary") -> str:
    """Analyze data and provide insights.

    Args:
        data: The data to analyze (numbers, text, etc.)
        analysis_type: Type of analysis (summary, trend, comparison)
    """
    return f"[{analysis_type.title()} analysis of data: '{data[:50]}...' - LLM will provide detailed analysis]"


# --- Build the multi-agent system ---


def build_supervisor_graph() -> Any:
    """Build a supervisor multi-agent system with durable execution.

    Creates a supervisor that coordinates three specialized agents:
    1. Researcher: Gathers information via web search
    2. Writer: Creates and summarizes content
    3. Analyst: Performs calculations and data analysis

    The supervisor decides which agent(s) to use based on the task,
    routes work appropriately, and synthesizes final results.

    With Temporal integration:
    - Each agent's execution runs as Temporal activities
    - Agent failures are automatically retried
    - Progress is checkpointed between agent handoffs
    - The entire multi-agent workflow survives worker crashes

    Returns:
        A compiled LangGraph supervisor that can be executed with ainvoke().
    """
    # Create the model
    model = ChatOpenAI(
        model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
        temperature=0,
    )

    # Create specialized agents

    # Researcher agent - gathers information
    researcher: Any = create_agent(
        model=model,
        tools=[web_search],
        name="researcher",
        system_prompt=(
            "You are a research specialist with web search capabilities. "
            "Your job is to find accurate, relevant information on any topic. "
            "Always cite what you find and be thorough in your research. "
            "If you can't find specific information, say so clearly."
        ),
    )

    # Writer agent - creates content
    writer: Any = create_agent(
        model=model,
        tools=[write_content, summarize],
        name="writer",
        system_prompt=(
            "You are a skilled writer and content creator. "
            "You excel at writing clear, engaging content and summarizing complex topics. "
            "Adapt your writing style to the requested format (blog, report, summary, etc.). "
            "Always structure your content logically with clear sections."
        ),
    )

    # Analyst agent - data analysis and calculations
    analyst: Any = create_agent(
        model=model,
        tools=[calculate, analyze_data],
        name="analyst",
        system_prompt=(
            "You are a data analyst expert in mathematical calculations and data interpretation. "
            "Use the calculate tool for any mathematical operations. "
            "Provide clear explanations of your analysis and methodology. "
            "Always double-check your calculations."
        ),
    )

    # Create the supervisor to coordinate the agents
    workflow = create_supervisor(
        agents=[researcher, writer, analyst],
        model=model,
        prompt=(
            "You are a team supervisor managing three specialized agents:\n"
            "- researcher: Has web search capabilities. Use for gathering information, "
            "facts, current events, or research tasks.\n"
            "- writer: Specializes in content creation and summarization. Use for "
            "writing articles, reports, summaries, or any content generation.\n"
            "- analyst: Expert in calculations and data analysis. Use for math problems, "
            "data interpretation, or analytical tasks.\n\n"
            "Your job is to:\n"
            "1. Understand the user's request\n"
            "2. Break it down into subtasks if needed\n"
            "3. Assign tasks to the appropriate agent(s)\n"
            "4. Synthesize the final response from agent outputs\n\n"
            "Assign work to one agent at a time. Do not do the work yourself - "
            "always delegate to the appropriate specialist."
        ),
        # Include full conversation history for context
        output_mode="full_history",
    )

    return workflow.compile()
