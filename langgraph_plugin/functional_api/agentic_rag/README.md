# Agentic RAG (Functional API)

Retrieval-Augmented Generation with document grading and query rewriting for improved answer quality.

## Overview

Unlike simple RAG, agentic RAG evaluates retrieved documents and adapts:

1. **Retrieve** - Fetch documents for the query
2. **Grade** - Evaluate document relevance
3. **Rewrite** - If not relevant, reformulate query
4. **Generate** - Create answer from relevant documents

## Architecture

```
User Question
      │
      ▼
┌─────────────────┐
│retrieve_documents│◄─────────┐
│     (task)       │          │
└────────┬─────────┘          │
         │                    │
         ▼                    │
┌─────────────────┐           │
│ grade_documents │           │
│     (task)      │           │
└────────┬────────┘           │
         │                    │
         ▼                    │
    Relevant?                 │
         │                    │
    YES  │    NO              │
         │     │              │
         │     ▼              │
         │  ┌──────────────┐  │
         │  │ rewrite_query│──┘
         │  │    (task)    │
         │  └──────────────┘
         ▼
┌─────────────────┐
│ generate_answer │
│     (task)      │
└─────────────────┘
```

## Key Code

### Adaptive Retrieval Loop

```python
@entrypoint()
async def agentic_rag_entrypoint(question: str, max_retries: int = 2) -> dict:
    current_query = question

    for attempt in range(max_retries + 1):
        # Retrieve documents
        documents = await retrieve_documents(current_query)

        # Grade for relevance
        grade_result = await grade_documents(question, documents)

        if grade_result["relevant"]:
            # Generate answer with relevant docs
            answer = await generate_answer(question, documents)
            return {"answer": answer, "status": "success"}

        # Rewrite query and retry
        if attempt < max_retries:
            current_query = await rewrite_query(current_query)

    # Best-effort answer with all retrieved docs
    return {"answer": await generate_answer(question, all_docs), "status": "max_retries"}
```

### Document Grading

```python
@task
def grade_documents(question: str, documents: list) -> dict:
    """Evaluate if documents are relevant to the question."""
    relevant_docs = [doc for doc in documents if is_relevant(doc, question)]
    return {
        "relevant": len(relevant_docs) >= threshold,
        "relevant_count": len(relevant_docs)
    }
```

## Why Temporal?

- **Reliability**: Multiple retrieval attempts complete reliably
- **Observability**: See which queries succeeded/failed
- **Retries**: Handle API failures in retrieval/LLM calls
- **Audit trail**: Track query rewrites in workflow history

## Running the Sample

1. Start Temporal:
   ```bash
   temporal server start-dev
   ```

2. Run with API key:
   ```bash
   export OPENAI_API_KEY=your-key
   uv run langgraph_plugin/functional_api/agentic_rag/run_worker.py
   ```

3. Execute a question:
   ```bash
   uv run langgraph_plugin/functional_api/agentic_rag/run_workflow.py
   ```

## Customization

### Adjust Relevance Threshold

```python
@task
def grade_documents(question: str, documents: list) -> dict:
    # Require more relevant documents
    return {"relevant": relevant_count >= 3}
```

### Add Query Transformation Strategies

```python
@task
def rewrite_query(query: str) -> str:
    strategies = ["simplify", "expand", "rephrase"]
    # Try different rewriting approaches
    ...
```
