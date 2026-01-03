"""Agentic RAG Workflow.

Temporal workflow for the agentic RAG system.
"""

from typing import Any

from temporalio import workflow
from temporalio.contrib.langgraph import compile


@workflow.defn
class AgenticRagWorkflow:
    """Temporal workflow for agentic RAG.

    The system:
    1. Retrieves documents based on query
    2. Grades documents for relevance
    3. Rewrites query and retries if not relevant
    4. Generates answer using relevant documents

    Each task runs as a Temporal activity with automatic retries.
    """

    @workflow.run
    async def run(self, question: str) -> dict[str, Any]:
        """Run the agentic RAG system.

        Args:
            question: The user's question.

        Returns:
            Answer with metadata.
        """
        app = compile("agentic_rag_entrypoint")
        result = await app.ainvoke(question)
        return result
