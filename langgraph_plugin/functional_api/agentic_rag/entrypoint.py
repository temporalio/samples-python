"""Agentic RAG Entrypoint Definition.

The @entrypoint function implements an agentic RAG pattern:
1. Retrieve documents based on query
2. Grade documents for relevance
3. If not relevant, rewrite query and retry
4. Generate answer using relevant documents
"""

from typing import Any

from langgraph.func import entrypoint

from langgraph_plugin.functional_api.agentic_rag.tasks import (
    generate_answer,
    grade_documents,
    retrieve_documents,
    rewrite_query,
)


@entrypoint()
async def agentic_rag_entrypoint(question: str, max_retries: int = 2) -> dict[str, Any]:
    """Run an agentic RAG system.

    The system will:
    1. Retrieve documents
    2. Grade them for relevance
    3. Rewrite query and retry if not relevant
    4. Generate answer from relevant documents

    Each @task call runs as a Temporal activity with automatic retries.

    Args:
        question: The user's question.
        max_retries: Maximum query rewrite attempts.

    Returns:
        Dict with answer, documents used, and metadata.
    """
    current_query = question
    all_documents: list[dict[str, Any]] = []

    for attempt in range(max_retries + 1):
        # Step 1: Retrieve documents
        documents = await retrieve_documents(current_query)
        all_documents.extend(documents)

        # Step 2: Grade documents
        grade_result = await grade_documents(question, documents)

        if grade_result["relevant"]:
            # Step 3: Generate answer with relevant documents
            answer = await generate_answer(question, documents)

            return {
                "question": question,
                "answer": answer,
                "documents_used": len(documents),
                "query_rewrites": attempt,
                "final_query": current_query,
                "status": "success",
            }

        # Documents not relevant - rewrite query if retries left
        if attempt < max_retries:
            current_query = await rewrite_query(current_query)

    # Max retries reached - generate best-effort answer
    answer = await generate_answer(question, all_documents)

    return {
        "question": question,
        "answer": answer,
        "documents_used": len(all_documents),
        "query_rewrites": max_retries,
        "final_query": current_query,
        "status": "max_retries_reached",
    }
