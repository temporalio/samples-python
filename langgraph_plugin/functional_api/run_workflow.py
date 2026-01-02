"""Execute the Functional API Proposal workflows.

This shows executing user-defined workflows that use the LangGraph functional API.
"""

import asyncio
import sys

from temporalio.client import Client
from temporalio.envconfig import ClientConfig

from langgraph_plugin.functional_api.workflow import (
    DocumentWorkflow,
    ReviewWorkflow,
)


async def run_document_workflow(client: Client) -> None:
    """Run the document generation workflow."""
    print("\n" + "=" * 60)
    print("Running DocumentWorkflow")
    print("=" * 60)

    result = await client.execute_workflow(
        DocumentWorkflow.run,
        "Artificial Intelligence",
        id="document-workflow-demo",
        task_queue="langgraph-functional",
    )

    print(f"\nResult: {result}")
    if "document" in result:
        doc = result["document"]
        print(f"\nDocument Title: {doc.get('title')}")
        print(f"Word Count: {doc.get('word_count')}")
        print(f"Section Count: {doc.get('section_count')}")
        print(f"\nContent Preview:\n{doc.get('content', '')[:200]}...")


async def run_review_workflow(client: Client) -> None:
    """Run the review workflow with human-in-the-loop.

    Demonstrates:
    - Starting workflow
    - Querying workflow status
    - Sending resume signal
    - Getting final result
    """
    print("\n" + "=" * 60)
    print("Running ReviewWorkflow (Human-in-the-Loop)")
    print("=" * 60)

    # Start workflow (don't wait for completion)
    handle = await client.start_workflow(
        ReviewWorkflow.run,
        "Machine Learning",
        id="review-workflow-demo",
        task_queue="langgraph-functional",
    )

    print("Workflow started. Generating draft...")

    # Wait a bit for the workflow to reach the interrupt point
    await asyncio.sleep(3)

    # Query current status
    status = await handle.query(ReviewWorkflow.get_status)
    print(f"\nStatus: {status}")

    if status.get("waiting_for_review"):
        print("Workflow is waiting for human review.")
        print(f"Draft document: {status.get('draft')}")

        # Simulate human review delay
        await asyncio.sleep(1)

        # Send resume signal with approval
        print("\nSending resume signal with approval...")
        await handle.signal(ReviewWorkflow.resume, {"decision": "approve", "notes": "Looks good!"})

    # Wait for workflow completion
    result = await handle.result()

    print(f"\nFinal Result: {result}")
    print(f"Status: {result.get('status')}")


async def run_review_workflow_with_revision(client: Client) -> None:
    """Run the review workflow and request revisions."""
    print("\n" + "=" * 60)
    print("Running ReviewWorkflow (with Revision Request)")
    print("=" * 60)

    handle = await client.start_workflow(
        ReviewWorkflow.run,
        "Deep Learning",
        id="review-workflow-revision-demo",
        task_queue="langgraph-functional",
    )

    print("Workflow started. Waiting for draft...")
    await asyncio.sleep(3)

    # Request revisions
    print("\nSending resume signal requesting revisions...")
    await handle.signal(
        ReviewWorkflow.resume,
        {"decision": "revise", "feedback": "Add more technical details"},
    )

    result = await handle.result()

    print(f"\nFinal Result: {result}")
    print(f"Status: {result.get('status')}")
    if result.get("feedback"):
        print(f"Feedback incorporated: {result.get('feedback')}")


async def main() -> None:
    """Run the workflow demonstrations."""
    config = ClientConfig.load_client_connect_config()
    config.setdefault("target_host", "localhost:7233")
    client = await Client.connect(**config)

    # Determine which workflow to run
    if len(sys.argv) > 1:
        workflow_name = sys.argv[1].lower()
    else:
        workflow_name = "document"

    if workflow_name == "document":
        await run_document_workflow(client)
    elif workflow_name == "review":
        await run_review_workflow(client)
    elif workflow_name == "revision":
        await run_review_workflow_with_revision(client)
    elif workflow_name == "all":
        await run_document_workflow(client)
        await run_review_workflow(client)
        await run_review_workflow_with_revision(client)
    else:
        print(f"Unknown workflow: {workflow_name}")
        print(
            "Usage: python -m langgraph_plugin.functional_api.run_workflow [document|review|revision|all]"
        )
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
