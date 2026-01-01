"""Task definitions for the Functional API sample.

Each @task function becomes a Temporal activity when registered
with LangGraphFunctionalPlugin.
"""

import asyncio
from typing import Any

from langgraph.func import task


@task
async def research_topic(topic: str) -> dict[str, Any]:
    """Research a topic and gather information.

    When executed via Temporal:
    - Runs as a Temporal activity with automatic retries
    - Result is checkpointed for workflow recovery
    - Can configure timeout, retry policy per task
    """
    await asyncio.sleep(0.5)  # Simulate API call

    return {
        "topic": topic,
        "facts": [
            f"Fact 1 about {topic}",
            f"Fact 2 about {topic}",
            f"Fact 3 about {topic}",
        ],
        "sources": ["source1.com", "source2.com"],
    }


@task
async def write_section(
    topic: str,
    section_name: str,
    research: dict[str, Any],
) -> str:
    """Write a section of content based on research."""
    await asyncio.sleep(0.3)

    facts = research.get("facts", [])
    facts_text = ", ".join(facts[:2]) if facts else "general information"

    templates = {
        "introduction": f"Welcome to our exploration of {topic}. Based on {facts_text}, we will discuss...",
        "body": f"The key aspects of {topic} include: {facts_text}. Furthermore...",
        "conclusion": f"In conclusion, {topic} is a fascinating subject. As we learned: {facts_text}.",
    }

    return templates.get(section_name, f"Section about {topic}: {facts_text}")


@task
async def compile_document(sections: list[str], title: str) -> dict[str, Any]:
    """Compile multiple sections into a final document."""
    await asyncio.sleep(0.2)

    full_content = "\n\n".join(sections)

    return {
        "title": title,
        "content": full_content,
        "word_count": len(full_content.split()),
        "section_count": len(sections),
    }
