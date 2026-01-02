"""Task definitions for the Supervisor Multi-Agent system.

Each agent's work runs as a @task (Temporal activity), providing automatic
retries and failure recovery for the entire multi-agent system.
"""

import os
from typing import Any, Literal

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langgraph.func import task
from pydantic import BaseModel, Field


class SupervisorDecision(BaseModel):
    """Supervisor's decision on which agent to use next."""

    next_agent: Literal["researcher", "writer", "analyst", "FINISH"] = Field(
        description="The next agent to route to, or FINISH if task is complete"
    )
    task_for_agent: str = Field(
        description="The specific task to give to the next agent"
    )
    reasoning: str = Field(description="Brief explanation of the routing decision")


# --- Tool implementations for agents ---


def web_search(query: str) -> str:
    """Mock web search for demonstration."""
    mock_results = {
        "ai trends 2024": (
            "Key AI trends in 2024:\n"
            "1. Multimodal AI models combining text, image, and video\n"
            "2. AI agents and autonomous systems\n"
            "3. Small language models for edge deployment"
        ),
        "temporal workflow": (
            "Temporal is a durable execution platform:\n"
            "- Workflows survive failures and can run for years\n"
            "- Activities are retried automatically on failure"
        ),
    }
    query_lower = query.lower()
    for key, result in mock_results.items():
        if any(word in query_lower for word in key.split()):
            return result
    return f"Search results for '{query}': General information found."


def calculate(expression: str) -> str:
    """Safely evaluate mathematical expressions."""
    try:
        allowed_chars = set("0123456789+-*/.() ")
        if not all(c in allowed_chars for c in expression):
            return "Error: Invalid characters"
        result = eval(expression)  # noqa: S307
        return str(result)
    except Exception as e:
        return f"Error: {e}"


@task
async def supervisor_decide(
    messages: list[dict[str, Any]], available_agents: list[str]
) -> dict[str, Any]:
    """Supervisor decides which agent should handle the next step.

    Args:
        messages: Conversation history.
        available_agents: List of available agent names.

    Returns:
        Dict with next_agent, task_for_agent, and reasoning.
    """
    model = ChatOpenAI(
        model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
        temperature=0,
    )

    agents_desc = """
- researcher: Has web search capabilities. Use for gathering information, facts, or research tasks.
- writer: Specializes in content creation and summarization.
- analyst: Expert in calculations and data analysis.
"""

    supervisor_prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                f"""You are a team supervisor managing specialized agents:
{agents_desc}

Based on the conversation, decide which agent should work next.
If the task is complete, respond with FINISH.
Always provide a specific task for the chosen agent.""",
            ),
            ("human", "Conversation so far:\n{conversation}\n\nDecide the next step:"),
        ]
    )

    # Format conversation
    conv_text = "\n".join(
        f"{m.get('role', 'unknown')}: {m.get('content', '')}" for m in messages
    )

    chain = supervisor_prompt | model.with_structured_output(SupervisorDecision)
    decision: Any = await chain.ainvoke({"conversation": conv_text})

    return {
        "next_agent": decision.next_agent,
        "task_for_agent": decision.task_for_agent,
        "reasoning": decision.reasoning,
    }


@task
async def researcher_work(task_description: str) -> str:
    """Researcher agent performs web search and information gathering.

    Args:
        task_description: The research task to perform.

    Returns:
        Research findings as a string.
    """
    model = ChatOpenAI(
        model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
        temperature=0,
    )

    # Perform search
    search_results = web_search(task_description)

    # Synthesize findings
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are a research specialist. Synthesize the search results into a clear summary.",
            ),
            (
                "human",
                f"Task: {task_description}\n\nSearch Results:\n{search_results}\n\nProvide your research summary:",
            ),
        ]
    )

    chain = prompt | model | StrOutputParser()
    summary = await chain.ainvoke({})

    return f"[Researcher] {summary}"


@task
async def writer_work(task_description: str, context: str = "") -> str:
    """Writer agent creates content or summaries.

    Args:
        task_description: The writing task to perform.
        context: Additional context from previous agents.

    Returns:
        Written content as a string.
    """
    model = ChatOpenAI(
        model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
        temperature=0.7,
    )

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are a skilled writer. Create clear, engaging content based on the task.",
            ),
            (
                "human",
                f"Task: {task_description}\n\nContext:\n{context}\n\nWrite your content:",
            ),
        ]
    )

    chain = prompt | model | StrOutputParser()
    content = await chain.ainvoke({})

    return f"[Writer] {content}"


@task
async def analyst_work(task_description: str, data: str = "") -> str:
    """Analyst agent performs calculations and data analysis.

    Args:
        task_description: The analysis task to perform.
        data: Data to analyze.

    Returns:
        Analysis results as a string.
    """
    model = ChatOpenAI(
        model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
        temperature=0,
    )

    # Check if there's a calculation needed
    analysis = ""
    if any(op in task_description for op in ["+", "-", "*", "/", "calculate"]):
        # Extract and evaluate expression
        analysis = f"Calculation: {calculate(task_description)}\n"

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are a data analyst. Provide clear analysis and insights.",
            ),
            (
                "human",
                f"Task: {task_description}\n\nData:\n{data}\n\nPrevious analysis:\n{analysis}\n\nProvide your analysis:",
            ),
        ]
    )

    chain = prompt | model | StrOutputParser()
    result = await chain.ainvoke({})

    return f"[Analyst] {result}"
