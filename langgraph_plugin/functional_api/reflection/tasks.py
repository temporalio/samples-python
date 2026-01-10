"""Task definitions for the Reflection Agent.

Each @task function runs as a Temporal activity, providing automatic retries
and failure recovery for LLM calls.
"""

import os
from typing import Any

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langgraph.func import task
from pydantic import BaseModel, Field


class Critique(BaseModel):
    """Critique of the generated content."""

    strengths: list[str] = Field(description="What's good about the content")
    weaknesses: list[str] = Field(description="What needs improvement")
    suggestions: list[str] = Field(description="Specific suggestions for improvement")
    quality_score: int = Field(description="Quality score from 1-10", ge=1, le=10)
    is_satisfactory: bool = Field(
        description="Whether the content meets quality standards (score >= 7)"
    )


@task
async def generate_content(task_description: str) -> str:
    """Generate initial content based on the task.

    Creates the first draft that will be refined through reflection.

    Args:
        task_description: The writing/generation task.

    Returns:
        The generated draft content.
    """
    model = ChatOpenAI(
        model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
        temperature=0.7,  # Slightly higher for creative generation
    )

    generate_prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """You are a skilled writer. Generate high-quality content based on
the given task. Focus on:
- Clarity and coherence
- Relevant information
- Engaging style
- Proper structure

Produce your best work on the first try.""",
            ),
            ("human", "{task}"),
        ]
    )

    chain = generate_prompt | model | StrOutputParser()
    draft = await chain.ainvoke({"task": task_description})

    return draft


@task
async def critique_content(
    task_description: str, draft: str, iteration: int
) -> dict[str, Any]:
    """Reflect on the current draft and provide critique.

    Analyzes the content for strengths, weaknesses, and
    provides specific improvement suggestions.

    Args:
        task_description: The original task.
        draft: The current draft content.
        iteration: Current iteration number.

    Returns:
        Dict with critique details including quality score.
    """
    model = ChatOpenAI(
        model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
        temperature=0,  # Lower for consistent critique
    )

    reflect_prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """You are a thoughtful critic and editor. Analyze the given content
and provide constructive feedback.

Consider:
- Does it fulfill the original task?
- Is it clear and well-structured?
- Is the information accurate and relevant?
- Is the style engaging and appropriate?
- What specific improvements would make it better?

Be specific and actionable in your feedback.
Score 7+ means the content is ready for publication.""",
            ),
            (
                "human",
                "Task: {task}\n\nDraft (iteration {iteration}):\n{draft}\n\nProvide your critique:",
            ),
        ]
    )

    critic = reflect_prompt | model.with_structured_output(Critique)
    critique: Any = await critic.ainvoke(
        {"task": task_description, "draft": draft, "iteration": iteration}
    )

    return {
        "strengths": critique.strengths,
        "weaknesses": critique.weaknesses,
        "suggestions": critique.suggestions,
        "quality_score": critique.quality_score,
        "is_satisfactory": critique.is_satisfactory,
    }


@task
async def revise_content(
    task_description: str, draft: str, critique: dict[str, Any]
) -> str:
    """Revise the content based on critique feedback.

    Incorporates the suggestions to produce an improved version.

    Args:
        task_description: The original task.
        draft: The current draft content.
        critique: The critique with suggestions.

    Returns:
        The revised content.
    """
    model = ChatOpenAI(
        model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
        temperature=0.7,
    )

    # Format the feedback
    strengths = critique.get("strengths", [])
    weaknesses = critique.get("weaknesses", [])
    suggestions = critique.get("suggestions", [])

    feedback = f"""
Strengths: {', '.join(strengths)}
Weaknesses: {', '.join(weaknesses)}
Suggestions: {', '.join(suggestions)}
"""

    revise_prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """You are a skilled writer revising your work based on feedback.
Carefully address each weakness and incorporate the suggestions while
preserving the strengths.

Produce an improved version that addresses the critique.""",
            ),
            (
                "human",
                "Original task: {task}\n\nCurrent draft:\n{draft}\n\nFeedback:\n{feedback}\n\nRevised version:",
            ),
        ]
    )

    chain = revise_prompt | model | StrOutputParser()
    revised = await chain.ainvoke(
        {"task": task_description, "draft": draft, "feedback": feedback}
    )

    return revised
