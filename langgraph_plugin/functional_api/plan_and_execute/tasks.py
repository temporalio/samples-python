"""Task definitions for the Plan-and-Execute Agent.

Each @task runs as a Temporal activity with automatic retries.
Demonstrates step-by-step plan execution with tool usage.
"""

import os
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.func import task
from pydantic import BaseModel, Field


class PlanStep(BaseModel):
    """A single step in the execution plan."""

    step_number: int = Field(description="The step number (1-indexed)")
    description: str = Field(description="What this step should accomplish")
    tool_hint: str = Field(
        description="Suggested tool to use (calculate, lookup, or analyze)"
    )


class Plan(BaseModel):
    """An execution plan with ordered steps."""

    objective: str = Field(description="The main objective to accomplish")
    steps: list[PlanStep] = Field(
        description="Ordered list of steps to execute", min_length=1, max_length=5
    )


# --- Tool definitions ---


@tool
def calculate(expression: str) -> str:
    """Evaluate a mathematical expression.

    Args:
        expression: A mathematical expression like "2 + 2" or "10 * 5"

    Returns:
        The result of the calculation
    """
    try:
        allowed_chars = set("0123456789+-*/.() ")
        if not all(c in allowed_chars for c in expression):
            return "Error: Invalid characters in expression"
        result = eval(expression)  # noqa: S307
        return f"Result: {result}"
    except Exception as e:
        return f"Error calculating: {str(e)}"


@tool
def lookup(topic: str) -> str:
    """Look up information about a topic.

    Args:
        topic: The topic to look up information about

    Returns:
        Information about the topic
    """
    knowledge = {
        "python": "Python is a high-level programming language known for its simplicity.",
        "temporal": "Temporal is a durable execution platform for reliable workflows.",
        "langgraph": "LangGraph is a library for building stateful LLM applications.",
        "agents": "AI agents use LLMs to make decisions and take actions autonomously.",
    }
    topic_lower = topic.lower()
    for key, value in knowledge.items():
        if key in topic_lower:
            return value
    return f"No specific information found about '{topic}'."


@tool
def analyze(data: str) -> str:
    """Analyze data or text and provide insights.

    Args:
        data: The data or text to analyze

    Returns:
        Analysis results
    """
    word_count = len(data.split())
    char_count = len(data)
    return f"Analysis: {word_count} words, {char_count} characters."


@task
async def create_plan(objective: str) -> dict[str, Any]:
    """Create an execution plan from the objective.

    Args:
        objective: The main task objective.

    Returns:
        Dict with objective and list of steps.
    """
    model = ChatOpenAI(
        model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
        temperature=0,
    )

    plan_prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """You are a planning agent. Given an objective, create a step-by-step
plan to accomplish it. Each step should be specific and actionable.

Available tools for execution:
- calculate: For mathematical computations
- lookup: For retrieving information about topics
- analyze: For analyzing data or text

Create 2-4 steps that can be executed sequentially.""",
            ),
            ("human", "Objective: {objective}"),
        ]
    )

    planner = plan_prompt | model.with_structured_output(Plan)
    plan: Any = await planner.ainvoke({"objective": objective})

    return {
        "objective": plan.objective,
        "steps": [
            {
                "step_number": s.step_number,
                "description": s.description,
                "tool_hint": s.tool_hint,
            }
            for s in plan.steps
        ],
    }


@task
async def execute_step(
    step_number: int, description: str, tool_hint: str
) -> dict[str, Any]:
    """Execute a single step using the appropriate tool.

    Args:
        step_number: The step number.
        description: What this step should accomplish.
        tool_hint: Suggested tool to use.

    Returns:
        Dict with step result and success status.
    """
    model = ChatOpenAI(
        model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
        temperature=0,
    )

    tools = [calculate, lookup, analyze]
    model_with_tools = model.bind_tools(tools)

    # Ask the model to execute the step
    messages = [
        SystemMessage(
            content=f"You are executing step {step_number} of a plan. "
            f"Complete this step: {description}\n"
            f"Suggested tool: {tool_hint}"
        ),
        HumanMessage(content=description),
    ]

    response = await model_with_tools.ainvoke(messages)

    # Execute any tool calls
    result_parts = []
    if hasattr(response, "tool_calls") and response.tool_calls:
        tools_by_name = {"calculate": calculate, "lookup": lookup, "analyze": analyze}
        for tc in response.tool_calls:
            tool_fn = tools_by_name.get(tc["name"])
            if tool_fn:
                try:
                    tool_result = tool_fn.invoke(tc["args"])
                    result_parts.append(f"{tc['name']}: {tool_result}")
                except Exception as e:
                    result_parts.append(f"{tc['name']}: Error - {e}")

    if response.content:
        result_parts.append(str(response.content))

    result = "\n".join(result_parts) if result_parts else "Step completed"

    return {
        "step_number": step_number,
        "description": description,
        "result": result,
        "success": True,
    }


@task
async def generate_response(objective: str, step_results: list[dict[str, Any]]) -> str:
    """Generate the final response summarizing the execution.

    Args:
        objective: The original objective.
        step_results: Results from all executed steps.

    Returns:
        The final response.
    """
    model = ChatOpenAI(
        model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
        temperature=0,
    )

    results_text = "\n".join(
        f"{r['step_number']}. {r['description']}: {r['result']}" for r in step_results
    )

    response_prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """You are a summarizer. Given an objective and the results of
executing a plan, provide a clear, concise final answer.

Focus on directly answering the original objective using the
gathered information.""",
            ),
            (
                "human",
                "Objective: {objective}\n\nExecution results:\n{results}\n\nProvide final answer:",
            ),
        ]
    )

    chain = response_prompt | model | StrOutputParser()
    response = await chain.ainvoke({"objective": objective, "results": results_text})

    return response
