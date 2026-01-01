"""Entrypoint definitions for the Functional API sample.

Each @entrypoint becomes a Temporal workflow when registered
with LangGraphFunctionalPlugin.
"""

from typing import Any

from langgraph.func import entrypoint
from langgraph.types import interrupt

from .tasks import compile_document, research_topic, write_section


@entrypoint()
async def document_workflow(topic: str) -> dict[str, Any]:
    """Create a document about a topic.

    Demonstrates:
    - Sequential task execution (research)
    - Parallel task execution (writing sections)
    - Task composition (compiling results)

    Each task call becomes a Temporal activity execution.
    """
    # Step 1: Research (single activity)
    research = await research_topic(topic)

    # Step 2: Write sections in parallel (3 concurrent activities)
    intro_future = write_section(topic, "introduction", research)
    body_future = write_section(topic, "body", research)
    conclusion_future = write_section(topic, "conclusion", research)

    intro = await intro_future
    body = await body_future
    conclusion = await conclusion_future

    # Step 3: Compile (single activity)
    document = await compile_document(
        sections=[intro, body, conclusion],
        title=f"A Guide to {topic}",
    )

    return {
        "document": document,
        "research": research,
        "status": "completed",
    }


@entrypoint()
async def review_workflow(topic: str) -> dict[str, Any]:
    """Document workflow with human-in-the-loop review.

    Demonstrates interrupt() for human review:
    - interrupt() pauses the Temporal workflow
    - Workflow waits for signal to resume
    - Resume with Command(resume=value)
    """
    # Generate draft
    research = await research_topic(topic)
    draft_sections = []

    for section_name in ["introduction", "body", "conclusion"]:
        section = await write_section(topic, section_name, research)
        draft_sections.append(section)

    draft = await compile_document(draft_sections, f"Draft: {topic}")

    # Human review - pauses workflow until signal received
    review_response = interrupt({
        "action": "review_document",
        "document": draft,
        "options": ["approve", "revise", "reject"],
    })

    decision = review_response.get("decision", "reject")

    if decision == "approve":
        return {"document": draft, "status": "approved"}
    elif decision == "revise":
        feedback = review_response.get("feedback", "")
        revised_sections = []
        for section_name in ["introduction", "body", "conclusion"]:
            section = await write_section(
                f"{topic} (revised: {feedback})", section_name, research
            )
            revised_sections.append(section)
        revised = await compile_document(revised_sections, f"Revised: {topic}")
        return {"document": revised, "status": "revised", "feedback": feedback}
    else:
        return {"document": None, "status": "rejected"}
