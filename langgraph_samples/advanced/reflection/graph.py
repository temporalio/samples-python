"""Reflection Agent Graph Definition.

This module implements a reflection agent that generates content, critiques it,
and iteratively improves until quality criteria are met.

The reflection pattern:
1. generate - Create initial content based on the prompt
2. reflect - Critique the content and identify improvements
3. revise - Incorporate feedback to improve the content
4. evaluate - Check if quality criteria are met
5. Loop until satisfied or max iterations reached

This pattern is useful for:
- Writing tasks (essays, code, documentation)
- Problem-solving (iterative refinement)
- Quality assurance (self-checking outputs)

Note: This module is only imported by the worker (not by the workflow).
LangGraph cannot be imported in the workflow sandbox.
"""

import os
from typing import Annotated, Any, Literal

from langchain_core.messages import BaseMessage, HumanMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field
from typing_extensions import TypedDict


class Critique(BaseModel):
    """Critique of the generated content."""

    strengths: list[str] = Field(description="What's good about the content")
    weaknesses: list[str] = Field(description="What needs improvement")
    suggestions: list[str] = Field(description="Specific suggestions for improvement")
    quality_score: int = Field(
        description="Quality score from 1-10", ge=1, le=10
    )
    is_satisfactory: bool = Field(
        description="Whether the content meets quality standards (score >= 7)"
    )


class ReflectionState(TypedDict):
    """State for the reflection agent graph.

    Attributes:
        messages: Conversation history.
        task: The writing/generation task.
        current_draft: The current version of the content.
        critiques: History of critiques for each iteration.
        iteration: Current iteration number.
        max_iterations: Maximum allowed iterations.
        final_content: The final approved content.
    """

    messages: Annotated[list[BaseMessage], add_messages]
    task: str
    current_draft: str
    critiques: list[Critique]
    iteration: int
    max_iterations: int
    final_content: str


def build_reflection_graph() -> Any:
    """Build a reflection agent graph.

    The graph implements an iterative improvement workflow:
    1. Generate initial content
    2. Reflect and critique
    3. Revise based on feedback
    4. Check quality and loop or finish

    Returns:
        A compiled LangGraph that can be executed with ainvoke().
    """
    model = ChatOpenAI(
        model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
        temperature=0.7,  # Slightly higher for creative generation
    )

    critic_model = ChatOpenAI(
        model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
        temperature=0,  # Lower for consistent critique
    )

    def generate(state: ReflectionState) -> dict[str, Any]:
        """Generate initial content based on the task.

        Creates the first draft that will be refined through reflection.
        """
        messages = state["messages"]
        task = next(
            (m.content for m in messages if isinstance(m, HumanMessage)),
            "Write a short paragraph",
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
        draft = chain.invoke({"task": str(task)})

        return {
            "task": str(task),
            "current_draft": draft,
            "iteration": 1,
            "max_iterations": state.get("max_iterations", 3),
            "critiques": [],
        }

    def reflect(state: ReflectionState) -> dict[str, Any]:
        """Reflect on the current draft and provide critique.

        Analyzes the content for strengths, weaknesses, and
        provides specific improvement suggestions.
        """
        task = state.get("task", "")
        draft = state.get("current_draft", "")
        iteration = state.get("iteration", 1)

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

        critic = reflect_prompt | critic_model.with_structured_output(Critique)
        critique = critic.invoke({"task": task, "draft": draft, "iteration": iteration})

        return {
            "critiques": state.get("critiques", []) + [critique],
            "messages": [
                {
                    "role": "assistant",
                    "content": f"Iteration {iteration} critique: Score {critique.quality_score}/10. "
                    f"{'Satisfactory!' if critique.is_satisfactory else 'Needs improvement.'}",
                }
            ],
        }

    def should_revise(state: ReflectionState) -> Literal["revise", "finalize"]:
        """Decide whether to revise or finalize.

        Routes to finalize if:
        - Content is satisfactory (score >= 7)
        - Max iterations reached

        Otherwise continues to revise.
        """
        critiques = state.get("critiques", [])
        iteration = state.get("iteration", 1)
        max_iterations = state.get("max_iterations", 3)

        if not critiques:
            return "revise"

        latest_critique = critiques[-1]

        # Finalize if satisfactory or max iterations reached
        if latest_critique.is_satisfactory or iteration >= max_iterations:
            return "finalize"

        return "revise"

    def revise(state: ReflectionState) -> dict[str, Any]:
        """Revise the content based on critique feedback.

        Incorporates the suggestions to produce an improved version.
        """
        task = state.get("task", "")
        draft = state.get("current_draft", "")
        critiques = state.get("critiques", [])
        iteration = state.get("iteration", 1)

        if not critiques:
            return {"iteration": iteration + 1}

        latest_critique = critiques[-1]

        # Format the feedback
        feedback = f"""
Strengths: {', '.join(latest_critique.strengths)}
Weaknesses: {', '.join(latest_critique.weaknesses)}
Suggestions: {', '.join(latest_critique.suggestions)}
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
        revised = chain.invoke({"task": task, "draft": draft, "feedback": feedback})

        return {
            "current_draft": revised,
            "iteration": iteration + 1,
            "messages": [
                {
                    "role": "assistant",
                    "content": f"Revised draft (iteration {iteration + 1}) created.",
                }
            ],
        }

    def finalize(state: ReflectionState) -> dict[str, Any]:
        """Finalize the content and prepare the response.

        Marks the current draft as final and creates the summary.
        """
        draft = state.get("current_draft", "")
        critiques = state.get("critiques", [])
        iteration = state.get("iteration", 1)

        # Get final score
        final_score = critiques[-1].quality_score if critiques else 0

        summary = f"""
Content finalized after {iteration} iteration(s).
Final quality score: {final_score}/10

--- FINAL CONTENT ---
{draft}
"""

        return {
            "final_content": draft,
            "messages": [{"role": "assistant", "content": summary}],
        }

    # Build the reflection graph
    workflow = StateGraph(ReflectionState)

    # Add nodes
    workflow.add_node("generate", generate)
    workflow.add_node("reflect", reflect)
    workflow.add_node("revise", revise)
    workflow.add_node("finalize", finalize)

    # Add edges
    workflow.add_edge(START, "generate")
    workflow.add_edge("generate", "reflect")

    # Conditional: revise or finalize based on critique
    workflow.add_conditional_edges(
        "reflect",
        should_revise,
        {"revise": "revise", "finalize": "finalize"},
    )

    # After revision, reflect again
    workflow.add_edge("revise", "reflect")

    workflow.add_edge("finalize", END)

    return workflow.compile()
